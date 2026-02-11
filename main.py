import os
import sys

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize logging FIRST — before any other imports that log on load
from logger_config import get_logger, log_session_start, log_session_end
log_session_start()
logger = get_logger(__name__)

from agent.temporal import TimeManager
from pipeline.packet_builder import PacketBuilder
from streaming.renderer_streaming import render_streaming, FALLBACK_MESSAGE
from agent.conversation import log_message, get_recent_history, buffer_clear, buffer_to_raw_text, start_new_session
from pipeline.summarizer_builder import run_summarizer_pipeline

def is_valid_response(response: str) -> bool:
    """
    Check if the AI response is valid and should be logged.
    Returns False for fallback messages and error messages.
    """
    # Check for fallback message
    if response == FALLBACK_MESSAGE:
        return False
    
    # Check for error messages
    if response.startswith("[Error:"):
        return False
    
    # Check for empty responses
    if not response or not response.strip():
        return False
    
    return True

def main():
    # Start a new conversation session (creates new log file)
    start_new_session()
    
    print("Sentient AI")

    # Initialize tools once
    timer = TimeManager()
    builder = PacketBuilder()
    logger.info("System initialized - TimeManager + PacketBuilder ready")
    
    # Stage 1: Session turn counter (T = 0)
    # Tracks turns within the current 5-turn cycle
    session_turn_count = 0
    CYCLE_SIZE = 5
    cycle_number = 0  # For Stage 3 indexing

    # === THE LOOP STARTS HERE ===
    while True:
        try:
            # 1. Input
            user_input = input("\nYOU : ")
            
            # Check for exit command BEFORE logging
            if user_input.strip().lower() in ["cls", "quit", "exit"]:
                logger.info("Session ended by user (exit command)")
                log_session_end()
                print("See you next time...")
                break
            
            # === GUARD: Empty Input ===
            if not user_input.strip():
                logger.debug("Empty input ignored")
                print("   >> [Traffic Control] Empty input ignored.")
                continue

            # === TRAFFIC CONTROL: Hold user input in temporary memory ===
            # Do NOT log yet - wait for AI to successfully respond
            pending_user_message = user_input
            logger.info(f"Request received - HOLD: \"{user_input[:80]}{'...' if len(user_input) > 80 else ''}\"")

            # 2. Time Subsystem
            timer.load_and_update()
            time_block = timer.get_time_block()

            # 3. Build Packet
            packet_content = builder.build(pending_user_message, time_block)
            logger.debug(f"Packet built - {len(packet_content)} chars")

            # 4. Output to File
            output_path = os.path.join(SCRIPT_DIR, "pipeline", "packet.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(packet_content)

            # 5. Render (Stream to LLM with typewriter effect)
            print(f"\nAI : ", end='', flush=True)
            logger.info("API call started - Streaming to Gemini")
            assistant_response = render_streaming(packet_content, char_delay=0.1)
            print()  # Newline after streaming completes
            logger.info(f"Response received - {len(assistant_response)} chars")
            
            # === TRAFFIC CONTROL: Conditional Commit ===
            # Only log if the response is valid (not fallback, not error)
            if is_valid_response(assistant_response):
                # COMMIT: Save BOTH user message AND AI response together
                log_message("user", pending_user_message)
                log_message("assistant", assistant_response)
                
                # Stage 1: Increment turn counter and check for 5-turn milestone
                session_turn_count += 1
                logger.info(f"COMMIT - Turn {session_turn_count}/{CYCLE_SIZE} (cycle #{cycle_number})")
                
                if session_turn_count >= CYCLE_SIZE:
                    # 5-turn milestone reached - trigger Stage 2 & 3
                    print("\n   [SUMMARIZER PIPELINE TRIGGERED - 5 turns reached]")
                    logger.info(f"Summarizer pipeline triggered - Cycle #{cycle_number}")
                    raw_conversation = buffer_to_raw_text()
                    
                    # Run the full summarization + indexing pipeline
                    compressed_memory = run_summarizer_pipeline(
                        raw_conversation, 
                        cycle_num=cycle_number
                    )
                    logger.info(f"Compressed memory: \"{compressed_memory[:120]}\"")
                    
                    print(f"   >> Compressed Memory: {compressed_memory}")
                    
                    # Reset for next cycle
                    buffer_clear()
                    session_turn_count = 0
                    cycle_number += 1
                    logger.debug(f"Buffer cleared - Starting cycle #{cycle_number}")
                    print(f"   >> Buffer cleared. Starting new cycle #{cycle_number}.\n")
            else:
                # AI response was invalid (fallback or error)
                # DISCARD: Do not save anything to logs
                logger.warning(f"DISCARD - Invalid response: \"{assistant_response[:80]}\"")
                print(f"   >> [Traffic Control] AI response invalid. Nothing saved to history.")
                print(f"   >> You can try again without polluting the conversation history.")

        except KeyboardInterrupt:
            # This catches 'Ctrl+C' so it exits cleanly
            logger.info("Session ended by user (Ctrl+C)")
            log_session_end()
            print("\n\nSYSTEM HALTED.")
            sys.exit()
        except Exception as e:
            logger.error(f"Unhandled error: {e}", exc_info=True)
            print(f"\nERROR: {e}")

if __name__ == "__main__":
    main()
