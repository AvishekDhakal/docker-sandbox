
# #dispatcher.py


# import docker
# import os
# import time
# import logging
# from watchdog.events import FileSystemEventHandler
# from watchdog.observers.polling import PollingObserver as Observer  # ← polling
# import stat

# import magic

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("dispatcher")

# UPLOAD_DIR = "/tmp/uploads"
# VOLUME_NAME = "streamlit-uploads"
# BIND_PATH    = "/executables"
# # os.makedirs(UPLOAD_DIR)
# client = docker.from_env()

# class NewFileHandler(FileSystemEventHandler):
#     def on_created(self, event):
#         if not event.is_directory:
#             self.process_file(event.src_path)

#     def on_moved(self, event):               # ← handle rename
#         if not event.is_directory:
#             self.process_file(event.dest_path)

#     def process_file(self, file_path):
#         logging.info(f"New file detected: {file_path}")
#         filename = os.path.basename(file_path)
#         file_type = magic.from_file(file_path)
#         st = os.stat(file_path)
#         os.chmod(file_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        
#         # Determine sandbox based on file type
#         if "ELF 64-bit LSB" in file_type or "ELF 32-bit LSB" in file_type:

#         # elif filename.endswith(".exe"):
#         #     image = "mcr.microsoft.com/windows/servercore:ltsc2019"
#         #     command = f"CMD /c {filename}"

#             try:
#                 # Start ephemeral sandbox
#                 container = client.containers.run(
#                     image       ="ubuntu:latest",
#                     command     = f"/executables/{filename}",
#                     volumes     = {
#                     VOLUME_NAME: {"bind": BIND_PATH, "mode":"ro"}
#                     },
#                     network     ="sandbox_net",
#                     detach      = True,
#                     # auto_remove = True,   # ← remove the container when it exits
#                 )
#                 logging.info(f"Spawned sandbox {container.short_id} for {filename}")
                
#             except docker.errors.DockerException as e:
#                 logger.error(f"Execution failed: {str(e)}")
    
#         else:
#             logger.warning(f"Unsupported file: {file_type}")
#             return

# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     handler = NewFileHandler()
#     observer = Observer()
#     observer.schedule(handler, UPLOAD_DIR, recursive=False)
#     observer.start()
#     logging.info("Dispatcher started. Watching for uploads…")
#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         observer.stop()
#     observer.join()



# dispatcher.py (excerpt)

import docker, os, logging, stat, magic,time
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver as Observer

logger = logging.getLogger("dispatcher")
UPLOAD_DIR     = "/tmp/uploads"
EXEC_MOUNT     = "/executables"
OUTPUT_MOUNT   = "/output"
UPLOAD_VOLUME  = "streamlit-uploads"
OUTPUT_VOLUME  = "sandbox-output"
SANDBOX_IMAGE = "avishekdhakal/linux-sandbox:1.0"
NETWORK_NAME   = "sandbox_net"

client = docker.from_env()

class NewFileHandler(FileSystemEventHandler):
    def process_file(self, file_path):
        filename = os.path.basename(file_path)
        # make executable
        st = os.stat(file_path)
        os.chmod(file_path, st.st_mode | stat.S_IXUSR)

        # only ELF for now
        if "ELF 64-bit LSB" in magic.from_file(file_path):
            try:
                container = client.containers.run(
                    image       = SANDBOX_IMAGE,
                    command     = [f"{EXEC_MOUNT}/{filename}"],
                    volumes     = {
                        UPLOAD_VOLUME: {"bind": EXEC_MOUNT, "mode": "ro"},
                        OUTPUT_VOLUME: {"bind": OUTPUT_MOUNT, "mode": "rw"},
                    },
                    network     = NETWORK_NAME,
                    detach      = True,
                    # auto_remove = True,
                )
                logger.info(f"Spawned sandbox {container.short_id} for {filename}")
            except docker.errors.DockerException as e:
                logger.error(f"Failed to launch sandbox: {e}")
        else:
            logger.warning(f"Unsupported file: {file_path}")

    def on_created(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.process_file(event.dest_path)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    handler = NewFileHandler()
    observer = Observer()
    observer.schedule(handler, UPLOAD_DIR, recursive=False)
    observer.start()
    logging.info("Dispatcher started. Watching for uploads…")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
