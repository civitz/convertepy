import sys

import psutil
import ffmpeg
import os
from multiprocessing import Pool, freeze_support, set_start_method
import PySimpleGUI as sg
from pathlib import Path, PureWindowsPath

# global variables
bitrates_and_frequencies = {
    "160kbps @ 44100 Hz": {"bitrate": "160k", "frequency": 44100},
    "128kbps @ 44100 Hz": {"bitrate": "128k", "frequency": 44100},
    "56kbps @ 22050 Hz": {"bitrate": "56k", "frequency": 22050}
}
bitrates_and_frequencies_choice = bitrates_and_frequencies.keys()
bf56k = "56kbps @ 22050 Hz"

def find_files(root):
    valid_extensions = (
        ".mp3",
        ".flac",
        ".aac",
        ".wav",
        ".wma"
    )
    out = []
    for path, subdirs, files in os.walk(root):
        for name in files:
            if name.lower().endswith(valid_extensions):
                relpath=os.path.relpath(os.path.join(path, name), root)
                out.append ((relpath,"found"))
    return out

def convert_single(source_file, dest_file, bitrate, frequency):
    print(f"Converting {str(source_file)} => {str(dest_file)} in mp3 {bitrate}kbps @ {frequency}Hz")
    stream = ffmpeg.input(str(source_file))
    stream.output(str(dest_file), format='mp3', acodec='libmp3lame', ac=2, ar=frequency,
                  audio_bitrate=bitrate).overwrite_output().run(capture_stdout=False)
    print(f"Converted {source_file} => {dest_file} in mp3 {bitrate}kbps @ {frequency}Hz!!!")

def convert_serial(files_to_process, root, destination_folder, bitrate_and_freq):
    bit_and_freq = bitrates_and_frequencies[bitrate_and_freq]
    out=[]
    for path, status in files_to_process:
        source_file = Path(root) / Path(path)
        dest_file = Path(destination_folder) / Path(path)
        dest_file_dir = dest_file.parent
        print(f"dest_file_dir:{dest_file_dir}")
        if not dest_file_dir.exists():
            print(f"creating {dest_file_dir}")
            dest_file_dir.mkdir(parents=True)
        convert_single(source_file,dest_file, bit_and_freq["bitrate"], bit_and_freq["frequency"])
        out.append((path, "converted"))
    return out

def convert_parallel(files_to_process, root, destination_folder, bitrate_and_freq):
    bit_and_freq = bitrates_and_frequencies[bitrate_and_freq]
    out = []
    cpu_count = psutil.cpu_count(logical=False)
    print(f"using {cpu_count} cpus")
    with Pool(cpu_count) as pool:
        for path, status in files_to_process:
            source_file = Path(root) / Path(path)
            dest_file = Path(destination_folder) / Path(path)
            dest_file_dir = dest_file.parent
            print(f"dest_file_dir:{dest_file_dir}")
            if not dest_file_dir.exists():
                print(f"creating {dest_file_dir}")
                dest_file_dir.mkdir(parents=True)
            pool.apply_async(convert_single,
                             args=[source_file, dest_file, bit_and_freq["bitrate"], bit_and_freq["frequency"]],
                             callback=lambda message, path=path: out.append((path, f"converted")),
                             error_callback=lambda err, path=path: out.append((path, f"ERROR: {err}")))
        print("End of pool")
        pool.close()
        pool.join()
        print("Joined")
    print("End of parallel")
    return out

def gui():
    files_to_process = []
    root = ""
    sg.theme('SystemDefault')   # Add a touch of color
    # All the stuff inside your window.
    layout = [[sg.Text('Select a folder with audio files', enable_events=False)],
              [sg.Input(key="SELECTED_FOLDER", expand_x=True, disabled=True, enable_events=True),
                       sg.FolderBrowse(enable_events=True)],
              [sg.Multiline(key="FILES", size=(100, 20))],
              [sg.Text('Bitrate and frequency:', enable_events=False), sg.Combo(values=list(bitrates_and_frequencies_choice), default_value=bf56k,
                        key="BITRATE_AND_FREQ"),
              [sg.Text('Destination:', enable_events=False), sg.Input(key="DESTINATION_FOLDER", expand_x=True, disabled=True, enable_events=True),
                       sg.FolderBrowse(enable_events=True)],
               sg.Push(), sg.Button("Reset"), sg.Button('Convert', key="CONVERT")]
              ]

    # Create the Window
    window = sg.Window('Window Title', layout)
    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read()
        print(f'Event {event}, {values}')
        if event == sg.WIN_CLOSED or event == 'Cancel': # if user closes window or clicks cancel
            break
        if event == "SELECTED_FOLDER":
            root = PureWindowsPath(Path(values["SELECTED_FOLDER"]))
            window["SELECTED_FOLDER"].update(root)
            files_to_process = find_files(root)
            files_to_process.sort(key=lambda x: x[0])
            new_text = "\r\n".join([f'{x[0]} ({x[1]})' for x in files_to_process])
            window["FILES"].update(new_text)
        if event == "DESTINATION_FOLDER":
            dest_folder = PureWindowsPath(Path(values["DESTINATION_FOLDER"]))
            window["DESTINATION_FOLDER"].update(dest_folder)
        if event == "CONVERT":
            files_to_process = convert_parallel(files_to_process,root, values["DESTINATION_FOLDER"], values["BITRATE_AND_FREQ"])
            files_to_process.sort(key=lambda x: x[0])
        #     window.perform_long_operation(lambda: convert_serial(files_to_process,root, values["DESTINATION_FOLDER"], values["BITRATE_AND_FREQ"]), "CONVERSION_END")
        # if event == "CONVERSION_END":
        #     files_to_process = values[event]
            new_text = "\r\n".join([f'{x[0]} ({x[1]})' for x in files_to_process])
            window["FILES"].update(new_text)

    window.close()

if __name__ == '__main__':
    freeze_support()
    set_start_method('spawn')
    sys.exit(gui())
