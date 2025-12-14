import asyncio
import logging

logger = logging.getLogger("collector.tor")

async def renew_tor_identity(control_host='tor', control_port=9051):
    """
    Signal Tor to switch identity (NEWNYM) via Control Port.
    """
    try:
        reader, writer = await asyncio.open_connection(control_host, control_port)
        
        # Authenticate (assumes no password set for internal usage)
        writer.write(b'AUTHENTICATE ""\r\n')
        await writer.drain()
        
        response = await reader.read(1024)
        if b'250 OK' not in response:
            logger.error(f"Tor Auth failed: {response}")
            writer.close()
            await writer.wait_closed()
            return False

        # Send NEWNYM signal
        writer.write(b'SIGNAL NEWNYM\r\n')
        await writer.drain()
        
        response = await reader.read(1024)
        if b'250 OK' not in response:
            logger.error(f"Tor Signal failed: {response}")
            writer.close()
            await writer.wait_closed()
            return False
            
        logger.info("[*] Tor identity rotation signal sent. Waiting 5s...")
        writer.close()
        await writer.wait_closed()
        
        # Wait for the circuit to be built
        await asyncio.sleep(5)
        return True

    except Exception as e:
        logger.error(f"Tor rotation failed: {e}")
        return False
