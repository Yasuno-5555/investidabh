import asyncio
import logging
import os

logger = logging.getLogger(__name__)

async def renew_tor_identity(
    control_host: str = 'tor',
    control_port: int = 9051,
    auth_password: str | None = None,
    timeout: float = 15.0
) -> bool:
    """
    Signal Tor to switch identity (NEWNYM) via Control Port.
    """
    try:
        # Establish connection with timeout
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(control_host, control_port),
            timeout=timeout
        )

        async def send_command(cmd: str) -> str | None:
            writer.write(f"{cmd}\r\n".encode())
            await writer.drain()
            
            # Read response properly (handling multi-line)
            lines = []
            while True:
                line = await reader.readline()
                if not line:
                    return None
                line = line.decode().rstrip()
                lines.append(line)
                if line.startswith("250 "):  # Final line starts with 250
                    break
            return "\n".join(lines)

        # 1. AUTHENTICATE
        auth_cmd = 'AUTHENTICATE' + (f' "{auth_password}"' if auth_password else ' ""')
        response = await send_command(auth_cmd)
        if response is None or "250 OK" not in response:
            logger.error(f"Tor authentication failed: {response}")
            writer.close()
            await writer.wait_closed()
            return False

        # 2. SIGNAL NEWNYM
        response = await send_command("SIGNAL NEWNYM")
        if response is None or "250 OK" not in response:
            logger.error(f"Tor NEWNYM signal failed: {response}")
            writer.close()
            await writer.wait_closed()
            return False

        logger.info("[*] Tor NEWNYM signal sent successfully.")

        writer.close()
        await writer.wait_closed()

        # Wait for circuit to stabilize (env dependent)
        build_time = float(os.getenv("TOR_CIRCUIT_BUILD_TIME", "10.0"))
        await asyncio.sleep(build_time)

        return True

    except asyncio.TimeoutError:
        logger.error("Tor control connection timed out")
        return False
    except Exception as e:
        logger.error(f"Tor identity rotation failed: {e}")
        return False
