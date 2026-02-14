from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest
from gateways.base import Gateway
import asyncio
import threading
import time

class TelegramGateway(Gateway):
    def __init__(self, token: str, on_message):
        super().__init__(on_message)
        if not token:
            raise ValueError("Telegram token is required")
        self.token = token

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Hello! I am Gemini Gateway. Ready to assist you.")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return
            
        user_id = str(update.effective_user.id)
        text = update.message.text
        
        # Send "thinking" indicator for long operations
        thinking_msg = await update.message.reply_text("⏳ Processing...")
        
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(None, self.on_message, user_id, text)
            
            # Delete the thinking message
            try:
                await thinking_msg.delete()
            except:
                pass
            
            if response:
                # Telegram has a 4096 char limit per message
                if len(response) > 4000:
                    for i in range(0, len(response), 4000):
                        await update.message.reply_text(response[i:i+4000])
                else:
                    await update.message.reply_text(response)
            else:
                 await update.message.reply_text("[No response from agent]")
        except Exception as e:
            print(f"Error handling telegram message: {e}")
            import traceback
            traceback.print_exc()
            try:
                await thinking_msg.delete()
            except:
                pass
            try:
                await update.message.reply_text(f"Error: {str(e)[:500]}")
            except Exception:
                pass

    def start(self):
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        print("Telegram Gateway thread started.")


    def stop(self):
        self.running = False
        print("Telegram Gateway stopping...")

    async def _async_run(self):
        """Manually manage the application lifecycle for full control."""
        max_retries = 5
        retry_count = 0
        self.running = True
        
        while retry_count < max_retries and self.running:
            app = None
            try:
                # Build application with generous timeouts
                # IMPORTANT: Only use .request() OR individual timeout methods, not both
                request = HTTPXRequest(
                    connect_timeout=120.0,
                    read_timeout=600.0,
                    write_timeout=600.0,
                    pool_timeout=120.0,
                )
                get_updates_request = HTTPXRequest(
                    connect_timeout=120.0,
                    read_timeout=600.0,
                    write_timeout=600.0,
                    pool_timeout=120.0,
                )
                
                app = (
                    ApplicationBuilder()
                    .token(self.token)
                    .request(request)
                    .get_updates_request(get_updates_request)
                    .build()
                )
                
                app.add_handler(CommandHandler("start", self._handle_start))
                app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self._handle_message))
                
                # Step 1: Initialize (this calls bot.get_me() which was timing out)
                print(f"Telegram: Initializing bot (attempt {retry_count + 1}/{max_retries})...")
                await app.initialize()
                print(f"Telegram: Bot initialized successfully! Bot username: @{app.bot.username}")
                
                # Step 2: Start the application
                await app.start()
                print("Telegram: Application started.")
                
                # Step 3: Start polling for updates
                await app.updater.start_polling(drop_pending_updates=True)
                print("Telegram: Polling for messages...")
                
                # Keep running until interrupted
                while self.running:
                    await asyncio.sleep(1)
                
                # Clean shutdown when self.running becomes False
                print("Telegram: Stopping loop...")
                if app.updater.running:
                    await app.updater.stop()
                if app.running:
                    await app.stop()
                await app.shutdown()
                print("Telegram: Shutdown complete.")
                break
                    
            except asyncio.CancelledError:
                print("Telegram: Shutting down...")
                break
            except Exception as e:
                retry_count += 1
                wait_time = min(10 * retry_count, 60)
                print(f"Telegram Gateway Error (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries and self.running:
                    print(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    print("Telegram Gateway: Max retries reached or stopped. Telegram bot is disabled.")
                    print("The HTTP Gateway is still running and functional.")
            finally:
                if app and self.running: # Only force cleanup if we crashed out of the loop unexpectedly
                    try:
                        if app.updater and app.updater.running:
                            await app.updater.stop()
                        if app.running:
                            await app.stop()

                        await app.shutdown()
                    except Exception:
                        pass

    def _run(self):
        """Run the async bot in a dedicated thread with its own event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_run())
        except Exception as e:
            print(f"Telegram Gateway thread error: {e}")
        finally:
            loop.close()


