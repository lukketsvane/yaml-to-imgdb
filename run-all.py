import subprocess
from colorama import Fore, Style

SCRIPTS = ["1-find-images.py", "2-process-pngs.py", "3-upload-to-ibb.py", "4-generate-and-deploy.py"]

if __name__ == "__main__":
    print(f"{Fore.YELLOW}Starting product catalog pipeline...{Style.RESET_ALL}")
    for script in SCRIPTS:
        try:
            print(f"{Fore.CYAN}Running {script}...")
            subprocess.run(["python3", script], check=True)
        except subprocess.CalledProcessError:
            print(f"{Fore.RED}Error in {script}, aborting!")
            exit(1)
    print(f"{Fore.GREEN}\nPipeline completed successfully! {Style.RESET_ALL}")