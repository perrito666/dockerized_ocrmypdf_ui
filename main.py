import atexit
import os
import sys
import subprocess
import shutil
import threading
import tkinter as tk
import tkinter.messagebox as messagebox
from tkinter.scrolledtext import ScrolledText
import webbrowser

DOCKER_IMAGE_BASE = "ocrmypdf-spanish"
DOCKER_IMAGE_VERSION = "1.0"
DOCKER_IMAGE_TAG = f"{DOCKER_IMAGE_BASE}:{DOCKER_IMAGE_VERSION}"

DOCKERFILE_NAME = "Dockerfile"
DOCKERFILE_CONTENT = """
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \\
    ocrmypdf \\
    tesseract-ocr \\
    tesseract-ocr-spa \\
    ghostscript \\
    qpdf \\
    unpaper \\
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["ocrmypdf"]
"""

def write_dockerfile_if_missing():
    if not os.path.exists(DOCKERFILE_NAME):
        with open(DOCKERFILE_NAME, "w") as f:
            f.write(DOCKERFILE_CONTENT.strip())

        def cleanup():
            if os.path.exists(DOCKERFILE_NAME):
                try:
                    os.remove(DOCKERFILE_NAME)
                except Exception:
                    pass
        atexit.register(cleanup)


class OCRApp:
    def __init__(self, root, pdf_file):
        self.root = root
        self.root.title("OCRmyPDF (Docker)")
        self.root.geometry("700x400")

        self.output = ScrolledText(root, state="normal", wrap="word")
        self.output.pack(expand=True, fill="both", padx=10, pady=10)
        self.output.configure(font=("Courier New", 10),
                              bg="white",
                              fg="black",
                              insertbackground="black"  # cursor color
                              )

        self.pdf_file = pdf_file
        self.log("Initializing...")

        # Start background thread
        threading.Thread(target=self.run, daemon=True).start()

    def log(self, text):
        self.output.configure(state="normal")
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)
        self.output.configure(state="disabled")
        # cheap debug technique
        # print(f"-> {text}")

    def stream_process(self, cmd, label):
        self.log(f"--- {label} ---")
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                self.log(line.strip())
            process.wait()
            return process.returncode
        except Exception as e:
            self.log(f"Error running {label}: {e}")
            return -1


    
    def run(self):
        if not shutil.which("docker"):
            self.log("Docker not found. Opening download page...")
            webbrowser.open("https://www.docker.com/products/docker-desktop/")
            return

        self.log("Docker found.")

        # Check if tagged image exists
        self.log(f"Checking for Docker image: {DOCKER_IMAGE_TAG}")
        inspect = subprocess.run(
            ["docker", "image", "inspect", DOCKER_IMAGE_TAG],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        if inspect.returncode != 0:
            self.log(f"Image {DOCKER_IMAGE_TAG} not found. Building now...")
            write_dockerfile_if_missing()
            code = self.stream_process(
                ["docker", "build", "-t", DOCKER_IMAGE_TAG, "."],
                f"Building Image {DOCKER_IMAGE_TAG}"
            )
            if code != 0:
                self.log("Docker build failed.")
                return
        else:
            self.log(f"Image {DOCKER_IMAGE_TAG} found. Skipping build.")

        # Prepare input/output paths
        if not os.path.isfile(self.pdf_file) or not self.pdf_file.lower().endswith(".pdf"):
            self.log("Invalid PDF file.")
            return

        input_path = os.path.abspath(self.pdf_file)
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_text{ext}"
        input_dir = os.path.dirname(input_path)
        input_file = os.path.basename(input_path)
        output_file = os.path.basename(output_path)

        self.log(f"Running OCR on: {input_file}")
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{input_dir}:/data",
            DOCKER_IMAGE_TAG,
            "-l", "spa", f"/data/{input_file}", f"/data/{output_file}"
        ]
        code = self.stream_process(cmd, f"OCR using {DOCKER_IMAGE_TAG}")

        if code == 0:
            self.log(f"✅ OCR complete.\nOutput saved as:\n{output_path}")
            self.root.after(100, self.show_completion_dialog)
        else:
            self.log("❌ OCR failed.")

    def show_completion_dialog(self):
        messagebox.showinfo("Terminé", "OCR terminé avec succès.")
        self.root.destroy()


def main():
    if len(sys.argv) != 2:
        print("Usage: drag and drop a PDF onto this executable.")
        sys.exit(1)

    pdf_file = sys.argv[1]

    root = tk.Tk()
    OCRApp(root, pdf_file)
    root.mainloop()

if __name__ == "__main__":
    main()

