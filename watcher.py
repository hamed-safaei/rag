from pathlib import Path
import shutil

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.services.pipeline import process_document

BASE = Path(__file__).resolve().parent

DATA = BASE / "app" / "data"

INCOMING = DATA / "incoming"
PROCESSING = DATA / "processing"
DONE = DATA / "done"
FAILED = DATA / "failed"

class PDFHandler(FileSystemEventHandler):

    def on_created(self, event):

        if event.is_directory:
            return

        file = Path(event.src_path)

        if file.suffix.lower() != ".pdf":
            return

        processing_file = PROCESSING / file.name

        shutil.move(file, processing_file)

        try:
            process_document(processing_file)

            shutil.move(processing_file, DONE / file.name)

            print(f"{file.name} processed successfully.")

        except Exception as e:

            print(e)

            shutil.move(processing_file, FAILED / file.name)


observer = Observer()
observer.schedule(PDFHandler(), str(INCOMING), recursive=False)

observer.start()

print("Watching incoming folder...")

try:
    while True:
        pass
except KeyboardInterrupt:
    observer.stop()

observer.join()