import tkinter as tk
import tkinter
import datetime
import platform
import subprocess
import os

# Holds information about what files have been selected to move.
# Persists through directory changes.
class MoveStateInfo:
    def __init__(self, current_directory_value, selected_files):
        self.initial_working_directory = current_directory_value
        self.file_names = []

        for file in selected_files:
            self.file_names.append(file.file_name)

# Enum for current file sorting state
class SortState:
    ALPHA = 1
    ALPHA_REVERSE = 2
    DATE_TIME = 4
    DATE_TIME_REVERSE = 8
    FILE_SIZE = 16
    FILE_SIZE_REVERSE = 32

# Holds all necessary information to interact with a file on the Android device
class FileDescriptor:
    # On select, set the file to unselected and then call the selection toggle function
    def select(self):
        self.is_selected = False
        try:
            modify_widget_states(enable_list=[self.checkbox_object])
            self.checkbox_object.deselect()
        # On exception, there is likely no UI elements associated with the File.
        # This can happen if a directory has been selected, such that invisible subfiles have been selected.
        # So call the toggle function directly without any reference to the label.
        except:
            on_file_select_toggle(self, None)
            return
        self.checkbox_object.invoke()

    def deselect(self):
        # On deselect, set the file to unselected and then call the selection toggle function
        self.is_selected = True
        try:
            modify_widget_states(enable_list=[self.checkbox_object])
            self.checkbox_object.select()
        except:
            # On exception, there is likely no UI elements associated with the File.
            # This can happen if a directory has been selected, such that invisible subfiles have been selected.
            # So call the toggle function directly without any reference to the label.
            on_file_select_toggle(self, None)
            return
        self.checkbox_object.invoke()            

    # Show human readable sizes rather than just bytes
    def calculate_human_readable_size(self):
        SIZE_PRESENTATIONS = ["B", "KB", "MB", "GB", "TB"]
        size_index = 0
        current_size = self.file_size_bytes

        def set_value(current_size):
            if current_size < 1000:
                self.file_size = "{} {}".format(current_size, SIZE_PRESENTATIONS[size_index])
                return True
            else:
                return False

        # Continue to divide the bytes count by 1000 until the value is below 1000
        # Then select the associated size presentation
        # e.g., bytes count = 1050, divide by 1000, = 50 KB
        while set_value(current_size) == False:
            current_size = int(current_size / 1000)
            size_index = size_index + 1

    def __init__(self, is_directory, file_name, file_absolute_directory_path, date_time, file_size_bytes):
        self.is_directory = is_directory
        self.file_name = file_name # Required for pulling & presentation
        self.file_name_compat = get_compatibility_name(self.file_name) # For Windows
        self.file_absolute_directory_path = file_absolute_directory_path # Required for pulling
        self.date_time = date_time # Required for presentation
        self.date_time_object = datetime.datetime.strptime(date_time, "%Y-%m-%d %H:%M") # Required for sorting (presentation)
        self.file_size_bytes = file_size_bytes # Required for presentation
        self.calculate_human_readable_size() 
        self.is_selected = False
        self.checkbox_object = None

CURRENT_OS = platform.system()

# Command constants

# All adb shell commands are wrapped by double quotes, with file paths then wrapped by single quotes
# There are two passes done to the command, which looks as follows for example:
# Supplied command on host:::  adb shell "ls '/sdcard/'"
# The host shell will parse it and then supply it to the adb shell, which will see this command:
# Received command on android::: ls '/sdcard/'
# Linux has very permissive file names, meaning they can have almost any symbol, which can break quotes...
# Assume a directory called John's_Photos, and no correction done to the supplied command:
#
# Supplied command on host:::  adb shell "ls '/sdcard/John's_Photos'"
# Received command on android::: ls '/sdcard/John's_Photos'
# As can be seen, the single quote in "John's" will break the ls command
# If the directory was: John"s_Photos, the command would break on the host before android would even receive it.
# Therefore, any path being supplied must be altered to escape any potential characters that may break or change the command
# All paths are sent through either quote_path_correctly_outer_double_inner_single or quote_path_correctly_outer_double

RUNTIME_ADB_COMMAND = ""
RUNTIME_OPEN_COMMAND = ""

ADB_WINDOWS = "adb.exe"
ADB_LINUX = "./adb"

OUTPUT_FOLDER = "output"
make_directory_path_value = os.path.join(os.path.abspath("."), OUTPUT_FOLDER) + "/"
os.makedirs(make_directory_path_value, exist_ok=True)
print("Creating output directory: {path}".format(path=make_directory_path_value))

OPEN_FILE_COMMAND_WINDOWS =  "start \"\" \"{absolute_file_path_on_host}\"" # https://superuser.com/a/239572
OPEN_FILE_COMMAND_LINUX = "xdg-open \"{absolute_file_path_on_host}\""

LIST_FILES_COMMAND = " shell \"ls -1a '{absolute_current_directory}'\""
LIST_FILES_AND_DETAILS_COMMAND = " shell \"ls -la '{absolute_current_directory}'\""
GET_FILE_EPOCH_COMMAND = " shell \"date -r '{absolute_file_path}' \"+%s\"\""
GET_DIRECTORY_KBYTE_SIZE_COMMAND = " shell \"du -sd 1 -k '{absolute_directory}'\""
PULL_FILE_COMMAND = " pull \"{absolute_file_path}\" \"{absolute_file_path_on_host}\""
MOVE_COMMAND = " shell \"mv '{absolute_file_path}' '{absolute_directory}'\""
DELETE_COMMAND = " shell \"rm -rf '{absolute_file_path}'\""
GET_TARGET_DIRECTORY_PATH = " shell \"echo \\`cd '{absolute_directory}' && pwd\\`\""
CREATE_DIRECTORY_COMMAND = " shell \"mkdir -p '{absolute_directory}'\""
GET_ALL_FILES_IN_DIRECTORY_RECURSIVELY_COMMAND = " shell \"find '{absolute_directory}' -type f\""

FILE_LIST_DETAIL_DATE_INDEX = 5
FILE_LIST_DETAIL_TIME_INDEX = 6
LS_FILE_BYTE_INDEX = 4
DIRECTORY_KBYTE_INDEX = 0

if CURRENT_OS == "Windows":
    RUNTIME_ADB_COMMAND = ADB_WINDOWS
    RUNTIME_OPEN_COMMAND = OPEN_FILE_COMMAND_WINDOWS
elif CURRENT_OS == "Linux":
    RUNTIME_ADB_COMMAND = ADB_LINUX
    RUNTIME_OPEN_COMMAND = OPEN_FILE_COMMAND_LINUX   

LIST_FILES_COMMAND = RUNTIME_ADB_COMMAND + LIST_FILES_COMMAND
LIST_FILES_AND_DETAILS_COMMAND = RUNTIME_ADB_COMMAND + LIST_FILES_AND_DETAILS_COMMAND
GET_FILE_EPOCH_COMMAND = RUNTIME_ADB_COMMAND + GET_FILE_EPOCH_COMMAND
GET_DIRECTORY_KBYTE_SIZE_COMMAND = RUNTIME_ADB_COMMAND + GET_DIRECTORY_KBYTE_SIZE_COMMAND
PULL_FILE_COMMAND = RUNTIME_ADB_COMMAND + PULL_FILE_COMMAND
MOVE_COMMAND = RUNTIME_ADB_COMMAND + MOVE_COMMAND
DELETE_COMMAND = RUNTIME_ADB_COMMAND + DELETE_COMMAND
OPEN_COMMAND = PULL_FILE_COMMAND + " && " + RUNTIME_OPEN_COMMAND
GET_TARGET_DIRECTORY_PATH = RUNTIME_ADB_COMMAND + GET_TARGET_DIRECTORY_PATH
CREATE_DIRECTORY_COMMAND = RUNTIME_ADB_COMMAND + CREATE_DIRECTORY_COMMAND
GET_ALL_FILES_IN_DIRECTORY_RECURSIVELY_COMMAND = RUNTIME_ADB_COMMAND + GET_ALL_FILES_IN_DIRECTORY_RECURSIVELY_COMMAND

# Constants
ILLEGAL_WINDOWS_CHARACTERS = ["<", ">", ":", "\"", "/", "\\", "|", "?", "*"]
UP_ARROW_STRING = "↑"
DOWN_ARROW_STRING = "↓"
MAX_LIST_LENGTH = 15

move_state_info_object = None

current_directory_value = "/sdcard/"
search_file_field_value = ""

sort_state = SortState.ALPHA

file_list_frame = None
current_directory_list = []
current_directory_list_index = 0
selected_files = set()
filtered_current_directory_list = []

# Toolbar Buttons
refresh_button = None
create_directory_button = None
pull_button = None
open_button = None
delete_button = None
move_button = None
current_directory_field = None
search_file_field = None
search_file_confirm_button = None
create_directory_field = None
#

# Sort Buttons
file_name_sort_button = None
FILE_NAME_SORT_BUTTON_STRING = "File Name"
date_time_sort_button = None
DATE_TIME_SORT_BUTTON_STRING = "Date Time"
file_size_sort_button = None
FILE_SIZE_SORT_BUTTON_STRING = "File Size"
file_select_or_clear_all_button = None
file_scrollup_button = None
file_scrolldown_button = None
#

root = tk.Tk()

root.geometry("1280x720")
root.title('ADB File Viewer')
root.resizable(0, 0)

####################
# Initialisations, called once...

# Create a frame to hold most of the buttons used to interact with the file system.
def create_toolbar():

    # Configure grid sizes

    toolbar_frame = tk.Frame(root, bg="red", width=1280, height=64)

    toolbar_frame_column_configure_array = []

    # By configuring the grid using an array of functions utilising an index,
    # As opposed to hard-coding,
    # It alows for very easy additions and removals of configuration options,
    # Without having to change everything before or after the addition or removal.

    # A weight of 0 should enforce the size specified

    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=384, weight=0)) # Current Directory TextBox
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=8, weight=0))
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=64, weight=0)) # Refresh
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=8, weight=0))
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=160, weight=0)) # Search File TextBox
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=8, weight=0))
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=64, weight=0)) # Search File OK  
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=8, weight=0))   
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=160, weight=0)) # Create Textbox
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=8, weight=0))   
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=64, weight=0)) # Create
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=8, weight=0))
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=64, weight=0)) # Pull
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=8, weight=0))
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=64, weight=0)) # Open
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=8, weight=0))
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=64, weight=0)) # Delete
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=8, weight=0))
    toolbar_frame_column_configure_array.append(lambda column_index : toolbar_frame.columnconfigure(column_index, minsize=64, weight=0)) # Move

    column_index = 0
    
    for toolbar_configure_column_function in toolbar_frame_column_configure_array:
        toolbar_configure_column_function(column_index)
        column_index = column_index + 1

    toolbar_frame.rowconfigure(0, minsize=64, weight=0)
    toolbar_frame.grid_propagate(0) # Should stop any resizing based on the size of the grid and added widgets
    toolbar_frame.pack()

    global refresh_button
    global create_directory_button
    global pull_button
    global open_button
    global delete_button
    global move_button
    global current_directory_field
    global search_file_field
    global search_file_confirm_button
    global create_directory_field

    configure_widget_array = []

    # A size of 1, followed by the use of the sticky attribute will ensure the widget fits the configured cell fully.

    # Similar logic to above with configuring the widgets by using an array of functions, thereby allowing easy additions and removals

    refresh_button = tk.Button(toolbar_frame, text="Refresh", width=1, height=1, command=refresh)
    create_directory_button = tk.Button(toolbar_frame, text="Create", width=1, height=1, command=on_create_directory)
    pull_button = tk.Button(toolbar_frame, text="Pull", width=1, height=1, command=on_pull)
    open_button = tk.Button(toolbar_frame, text="Open", width=1, height=1, command=on_open)
    move_button = tk.Button(toolbar_frame, text="Move", width=1, height=1, command=on_move)
    delete_button = tk.Button(toolbar_frame, text="Delete", width=1, height=1, command=on_delete)
    current_directory_field = tk.Text(toolbar_frame, width=1, height=1)
    current_directory_field.insert(tkinter.END, current_directory_value) # Pre-fill cwd field with default string /sdcard/
    search_file_field = tk.Text(toolbar_frame, width=1, height=1)
    search_file_confirm_button = tk.Button(toolbar_frame, text="Search", width=1, height=1, command=on_search)
    create_directory_field = tk.Text(toolbar_frame, width=1, height=1)

    modify_widget_states(disable_list=[pull_button, open_button, move_button, delete_button])

    configure_widget_array.append(lambda column_index : current_directory_field.grid(column=column_index, row=0, sticky="ew"))
    configure_widget_array.append(lambda column_index : refresh_button.grid(column=column_index, row=0, sticky="nsew"))
    configure_widget_array.append(lambda column_index : search_file_field.grid(column=column_index, row=0, sticky="ew"))
    configure_widget_array.append(lambda column_index : search_file_confirm_button.grid(column=column_index, row=0, sticky="nsew"))    
    configure_widget_array.append(lambda column_index : create_directory_field.grid(column=column_index, row=0, sticky="ew"))
    configure_widget_array.append(lambda column_index : create_directory_button.grid(column=column_index, row=0, sticky="nsew"))
    configure_widget_array.append(lambda column_index : pull_button.grid(column=column_index, row=0, sticky="nsew"))
    configure_widget_array.append(lambda column_index : open_button.grid(column=column_index, row=0, sticky="nsew"))
    configure_widget_array.append(lambda column_index : move_button.grid(column=column_index, row=0, sticky="nsew"))
    configure_widget_array.append(lambda column_index : delete_button.grid(column=column_index, row=0, sticky="nsew"))

    column_index = 0

    for configure_widget_function in configure_widget_array:
        configure_widget_function(column_index)
        column_index = column_index + 2 # Skip by 2 as every odd element is padding

# A seperator between frames

def create_separator():
    seperator_frame = tk.Frame(root, bg="black", width=1280, height=16)
    seperator_frame.rowconfigure(0, minsize=16, weight=0)
    seperator_frame.grid_propagate(0)
    seperator_frame.pack()

# Create a frame to hold most of the buttons used to provide presentation functionality of the file system
def create_sort_bar():
    sort_frame = tk.Frame(root, bg="green", width=1280, height=32)

    # Same creation logic as toolbar frame

    sort_frame_column_configure_array = []

    sort_frame_column_configure_array.append(lambda column_index : sort_frame.columnconfigure(column_index, minsize=368, weight=0)) # Space
    sort_frame_column_configure_array.append(lambda column_index : sort_frame.columnconfigure(column_index, minsize=128, weight=0)) # File Name
    sort_frame_column_configure_array.append(lambda column_index : sort_frame.columnconfigure(column_index, minsize=368, weight=0))
    sort_frame_column_configure_array.append(lambda column_index : sort_frame.columnconfigure(column_index, minsize=128, weight=0)) # DateTime
    sort_frame_column_configure_array.append(lambda column_index : sort_frame.columnconfigure(column_index, minsize=24, weight=0))
    sort_frame_column_configure_array.append(lambda column_index : sort_frame.columnconfigure(column_index, minsize=128, weight=0)) # File Size
    sort_frame_column_configure_array.append(lambda column_index : sort_frame.columnconfigure(column_index, minsize=12, weight=0))
    sort_frame_column_configure_array.append(lambda column_index : sort_frame.columnconfigure(column_index, minsize=32, weight=0)) # Select/Clear All
    sort_frame_column_configure_array.append(lambda column_index : sort_frame.columnconfigure(column_index, minsize=12, weight=0))
    sort_frame_column_configure_array.append(lambda column_index : sort_frame.columnconfigure(column_index, minsize=32, weight=0)) # Up Button
    sort_frame_column_configure_array.append(lambda column_index : sort_frame.columnconfigure(column_index, minsize=4, weight=0))
    sort_frame_column_configure_array.append(lambda column_index : sort_frame.columnconfigure(column_index, minsize=32, weight=0)) # Down Button  

    column_index = 0

    for sort_frame_column_configure_function in sort_frame_column_configure_array:
        sort_frame_column_configure_function(column_index)
        column_index = column_index + 1

    sort_frame.rowconfigure(0, minsize=32, weight=0)
    sort_frame.grid_propagate(0)
    sort_frame.pack()

    global file_name_sort_button
    global date_time_sort_button
    global file_size_sort_button
    global file_select_or_clear_all_button
    global file_scrollup_button 
    global file_scrolldown_button

    configure_widget_array = []

    file_name_sort_button = tk.Button(sort_frame, text=FILE_NAME_SORT_BUTTON_STRING + " " + UP_ARROW_STRING, width=1, height=1, command=on_file_name_sort)
    date_time_sort_button = tk.Button(sort_frame, text=DATE_TIME_SORT_BUTTON_STRING, width=1, height=1, command=on_date_time_sort)
    file_size_sort_button = tk.Button(sort_frame, text=FILE_SIZE_SORT_BUTTON_STRING, width=1, height=1, command=on_file_size_sort)
    file_scrollup_button = tk.Button(sort_frame, text=UP_ARROW_STRING, width=1, height=1, command=on_arrow_up)
    modify_widget_states(disable_list=[file_scrollup_button]) # Impossible to scroll-up on initialisation
    file_scrolldown_button = tk.Button(sort_frame, text=DOWN_ARROW_STRING, width=1, height=1, command=on_arrow_down)
    file_select_or_clear_all_button = tk.Button(sort_frame, width=1, height=1, text="*", command=on_select_or_clear_all)

    configure_widget_array.append(lambda column_index : file_name_sort_button.grid(column=column_index, row=0, sticky="nsew"))
    configure_widget_array.append(lambda column_index : date_time_sort_button.grid(column=column_index, row=0, sticky="nsew"))
    configure_widget_array.append(lambda column_index : file_size_sort_button.grid(column=column_index, row=0, sticky="nsew"))
    configure_widget_array.append(lambda column_index : file_select_or_clear_all_button.grid(column=column_index, row=0, sticky="nsew"))
    configure_widget_array.append(lambda column_index : file_scrollup_button.grid(column=column_index, row=0, sticky="nsew"))
    configure_widget_array.append(lambda column_index : file_scrolldown_button.grid(column=column_index, row=0, sticky="nsew"))

    column_index = 1

    for configure_widget_function in configure_widget_array:
        configure_widget_function(column_index)
        column_index = column_index + 2


####################
# General functions, can be called at any point during interactions with the application

# Query the file system for all files
def get_file_list():
    # Some DateTimes are extended and contain too much information,
    # This will reduce it by removing anything like seconds or miliseconds. e.g. 2000-01-01 23:45:00.087116584 +1100
    # Ensuring that the date time string is of a form like: "2000-01-01 23:45"
    def format_date_time_string(date_time_string, date_index, time_index):
        date_time_string_split_list = filter_empty_string_elements(date_time_string.split())
        file_date = date_time_string_split_list[date_index] # 2000-01-01
        # 23:45:00.087116584 -> # [23:45:00, 087116584] -> [23, 45, 00]
        file_time_unformatted = date_time_string_split_list[time_index].split(".")[0].split(":") 
        file_time = file_time_unformatted[0] + ":" + file_time_unformatted[1] # [23, 45, 00] -> 23:45
        return file_date + " " + file_time # 2000-01-01 23:45
    
    current_directory_list.clear()

    # Run a detailed ls command to retrieve information such as file type, size and date modified
    command = LIST_FILES_AND_DETAILS_COMMAND.format(absolute_current_directory=quote_path_correctly_outer_double_inner_single(current_directory_value))
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    print("Command run: {command}".format(command=command))
    # The first 3 elements after splitting by \n are total size, ".", and "..", none of which we want.
    file_list_details = filter_empty_string_elements(result.stdout.split("\n"))[3:]

    # Run a simple ls command to just get file names - helps when dealing with a file name that has spaces.
    command = LIST_FILES_COMMAND.format(absolute_current_directory=quote_path_correctly_outer_double_inner_single(current_directory_value))
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    print("Command run: {command}".format(command=command))
    # The first 2 elements after splitting by \n are ".", and "..", none of which we want.
    file_list = filter_empty_string_elements(result.stdout.split("\n"))[2:]
    
    for file_index in range(0, len(file_list)):
        is_directory = False
        file_name = file_list[file_index]
        file_date_time = ""
        file_size = 0

        # The first value in the detailed ls command will be "d" if the file is a directory
        if file_list_details[file_index][0].lower() == "d":
            is_directory = True

        # Split the detailed line by all whitespace, remove any empty elements, and then retrieve the size of the file in bytes
        if is_directory == False:
            file_size = int(filter_empty_string_elements(file_list_details[file_index].split())[LS_FILE_BYTE_INDEX])
        else:
            # If the file is a directory, then the du command has to be used.
            command = GET_DIRECTORY_KBYTE_SIZE_COMMAND.format(absolute_directory=quote_path_correctly_outer_double_inner_single(current_directory_value + file_list[file_index]))
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            print("Command run: {command}".format(command=command))
            # du in adb appears to only support KB as a minimum size, so to make it compatible with the file constructor which requires bytes, multiply the output by 1000
            file_size = int(filter_empty_string_elements(result.stdout.split())[DIRECTORY_KBYTE_INDEX]) * 1000         

        file_date_time = format_date_time_string(file_list_details[file_index], FILE_LIST_DETAIL_DATE_INDEX, FILE_LIST_DETAIL_TIME_INDEX)

        try:
            new_file_descriptor = FileDescriptor(is_directory, file_name, current_directory_value, file_date_time, file_size)
        except:
            # The only possible exception here is if the date time extracted from ls was wrong,
            # in which case we can fall back to another command which should work (but is slower)
            try:
                command = GET_FILE_EPOCH_COMMAND.format(absolute_file_path=current_directory_value + file_list[file_index])
                result = subprocess.run(command, capture_output=True, text=True, shell=True)
                print("Command run: {command}".format(command=command))
                file_date_time_timestamp = int(result.stdout.rstrip())
                file_date_time = format_date_time_string(str(datetime.datetime.fromtimestamp(file_date_time_timestamp)), 0, 1)
                new_file_descriptor = FileDescriptor(is_directory, file_name, current_directory_value, file_date_time, file_size)
            except:
                # Unknown issue, try next file
                continue

        current_directory_list.append(new_file_descriptor)
        
# Present all files returned from query    
# Create a frame to hold a certain amount of files row by row.
# Frame must be recreated when showing new files (e.g. when scrolling down)    
def display_file_list():
    global file_list_frame

    if file_list_frame is not None:
        file_list_frame.forget()
        file_list_frame.destroy()

    # Same creation logic as toolbar frame
    
    file_list_frame = tk.Frame(root, bg="light blue", width=1280, height=592)

    file_list_frame_column_configure_array = []
    file_list_frame_column_configure_array.append(lambda column_index : file_list_frame.columnconfigure(column_index, minsize=32, weight=0)) # Icon
    file_list_frame_column_configure_array.append(lambda column_index : file_list_frame.columnconfigure(column_index, minsize=8, weight=0))
    file_list_frame_column_configure_array.append(lambda column_index : file_list_frame.columnconfigure(column_index, minsize=782, weight=0)) # File Name
    file_list_frame_column_configure_array.append(lambda column_index : file_list_frame.columnconfigure(column_index, minsize=8, weight=0))
    file_list_frame_column_configure_array.append(lambda column_index : file_list_frame.columnconfigure(column_index, minsize=192, weight=0)) # Date Time
    file_list_frame_column_configure_array.append(lambda column_index : file_list_frame.columnconfigure(column_index, minsize=8, weight=0))
    file_list_frame_column_configure_array.append(lambda column_index : file_list_frame.columnconfigure(column_index, minsize=96, weight=0)) # File Size
    file_list_frame_column_configure_array.append(lambda column_index : file_list_frame.columnconfigure(column_index, minsize=16, weight=0))
    file_list_frame_column_configure_array.append(lambda column_index : file_list_frame.columnconfigure(column_index, minsize=64, weight=0)) # Select Box
    
    column_index = 0

    for file_list_column_configure_function in file_list_frame_column_configure_array:
        file_list_column_configure_function(column_index)
        column_index = column_index + 1

    # The current directory list may need to be filtered depending on the state of the program
    # If the program is in a "Move file state", then only directories should be presented
    # If the program is in a "Search file state", only valid files should be presented
    # If both states are active, then only valid directories should be presented

    global filtered_current_directory_list

    filtered_move_state_directory_list = []
    filtered_search_file_directory_list = []

    # If in move state, add all directories to the directory list
    if move_state_info_object is not None:
        for file_descriptor in current_directory_list:
            if file_descriptor.is_directory == True:
                filtered_move_state_directory_list.append(file_descriptor)
    # If in search state, add all valid files to the search file list
    if len(search_file_field_value) > 0:
        for file_descriptor in current_directory_list:
            if search_file_field_value.lower() in file_descriptor.file_name.lower():
                filtered_search_file_directory_list.append(file_descriptor)
    
    # If in move state...
    if move_state_info_object is not None:
        # and if in search state...
        if len(search_file_field_value) > 0:
            # Only keep directories that match the search value
            filtered_move_state_directory_list = list(filter(lambda search_file_name : search_file_name in filtered_move_state_directory_list, filtered_search_file_directory_list))
        # Set the filtered directory list to the move state directory list
        filtered_current_directory_list = filtered_move_state_directory_list
    # else if in search state
    elif len(search_file_field_value) > 0:
        # set the filtered directory list to the search file directory list
        filtered_current_directory_list = filtered_search_file_directory_list
    else:
        # set the filtererd directory list to the normal current directory list
        filtered_current_directory_list = current_directory_list

    row_index = 0

    # Add the ".." directory to the top of list always. Date and size does not matter.
    # Presents a maximum of MAX_LIST_LENGTH files, starting from current_directory_list_index
    # current_directory_list_index is changed by the scroll up and scroll down buttons
    for file_descriptor in ([FileDescriptor(True, "..", current_directory_value ,"1970-01-01 11:00", 0)] + filtered_current_directory_list)[current_directory_list_index : current_directory_list_index + MAX_LIST_LENGTH]:

        configure_widget_array = []

        file_icon_button = tk.Label(file_list_frame, text="D" if file_descriptor.is_directory else "F", width=1, height=1)

        # Lambdas which reference a variable in an outer scope bind to the "label", but not the value.
        # For example, if a new lambda is created every iteration, 
        # and each lambda binds to an iteration_count variable, 
        # and there are 10 iterations
        # and then each lambda is called after the loop is completed, 
        # then each lambda will get the same value from the index (9), as that is the final value of the iteration_count

        # To actually hold the value at the time of lambda creation, a double lambda is required.
        # The outer lambda must accept the outer scope variable as an argument, 
        # and then return an inner lambda which references the outer lambda's parameter
        # The outer lambda should be called immediately, thus returning the desired inner lambda which holds the desired value,
        # which can then be called when desired.

        # Only directories should be clickable
        # If directory, clicking will move into that directory
        if file_descriptor.is_directory == False:
            file_name_label = tk.Label(file_list_frame, text=file_descriptor.file_name, width=1, height=1)
        else:
            # Double lambda for on_directory_clicked so this file is passed to the function correctly
            file_name_label = tk.Button(file_list_frame, text=file_descriptor.file_name, width=1, height=1, command=(lambda current_file_descriptor : lambda : on_directory_clicked(current_file_descriptor))(file_descriptor))

        file_datetime_label = tk.Label(file_list_frame, text=file_descriptor.date_time, width=1, height=1)
        file_filesize_label = tk.Label(file_list_frame, text=file_descriptor.file_size, width=1, height=1)
        # Double lambda for on_file_select_toggle, so this file and its label are passed to the function correctly
        file_select_button = tk.Checkbutton(file_list_frame, command=(lambda current_file_descriptor, current_file_name_label : lambda : on_file_select_toggle(current_file_descriptor, current_file_name_label))(file_descriptor, file_name_label), width=1, height=1)

        # The ".." directory should not be selectable
        if file_descriptor.file_name == ".." or move_state_info_object is not None:
            modify_widget_states(disable_list=[file_select_button])

        configure_widget_array.append(lambda column_index : file_icon_button.grid(column=column_index, row=row_index, sticky="nsew"))
        configure_widget_array.append(lambda column_index : file_name_label.grid(column=column_index, row=row_index, sticky="nsew"))
        configure_widget_array.append(lambda column_index : file_datetime_label.grid(column=column_index, row=row_index, sticky="nsew"))
        configure_widget_array.append(lambda column_index : file_filesize_label.grid(column=column_index, row=row_index, sticky="nsew"))
        configure_widget_array.append(lambda column_index : file_select_button.grid(column=column_index, row=row_index, sticky="nsew"))

        column_index = 0

        for configure_widget_function in configure_widget_array:
            configure_widget_function(column_index)
            column_index = column_index + 2

        # If a file selection is made, and then a scroll is done, other checkboxes become ticked for some reason. So deselection is done by default
        file_select_button.deselect()
        file_descriptor.checkbox_object = file_select_button

        # Useful when the move button is clicked in the same directoy as it started,
        # Thereby goggling off the move state but presenting to the user what files they still have selected.
        if file_descriptor.is_selected == True:
            file_descriptor.select()

        file_list_frame.rowconfigure(row_index, minsize=32, weight=0)
        row_index = row_index + 1
        file_list_frame.rowconfigure(row_index, minsize=8, weight=0)
        row_index = row_index + 1

    file_list_frame.grid_propagate(0)
    file_list_frame.pack()

# Windows has file name restrictions which have to be considered when pulling a file from Android (Linux)
def get_compatibility_name(name):
    new_name = name

    for illegal_windows_character in ILLEGAL_WINDOWS_CHARACTERS:
        if illegal_windows_character in name:
            new_name = new_name.replace(illegal_windows_character, "")

    return new_name

# Queries the file system for files in the currently selected directory
# (Which can be directly specified in the field UI widget)
# Clears out all selections
# and presents the files to the user, starting from the top, in their desired sorting style.
def refresh():
    global current_directory_value
    # Get the current directory field value
    current_directory_value = current_directory_field.get("1.0", tkinter.END).rstrip()
    if current_directory_value[-1] != "/":
        # Ensure that it is terminated by a "/"
        current_directory_value = current_directory_value + "/"
    current_directory_field.delete(1.0, tkinter.END)
    # Clear out the field and rewrite it, just in case.
    current_directory_field.insert(tkinter.END, current_directory_value)
    on_unselect_all()
    get_file_list()
    redraw()
    scroll_to_top()

# Will not query the file system, will simply do a re-sort and re-draw based on the current configuration
def redraw():
    sort_directory_list_by_state()
    sort_directory_list_by_directory()
    display_file_list()    

# Easy way to mass change widget states
def modify_widget_states(enable_list = [], disable_list = []):
    for widget in enable_list:
        widget["state"] = "active"
    for widget in disable_list:
        widget["state"] = "disabled"

# Sometimes when splitting a string, it produces empty elements in the returned list.
# This removes them.
def filter_empty_string_elements(string_array):
    return list(filter(lambda string_element : len(string_element) > 0, string_array))

# Regardless of sorting style, directories should come before files
def sort_directory_list_by_directory():
    current_directory_list.sort(key=lambda element : 0 if element.is_directory == False else 1, reverse=True)

# Based on the enum, sort the current_directory_list appropriately.
def sort_directory_list_by_state():
    if sort_state == SortState.ALPHA:
        current_directory_list.sort(key=lambda element : element.file_name.lower())
    if sort_state == SortState.ALPHA_REVERSE:
        current_directory_list.sort(key=lambda element : element.file_name.lower(), reverse=True)
    if sort_state == SortState.DATE_TIME:
        current_directory_list.sort(key=lambda element : element.date_time_object)
    if sort_state == SortState.DATE_TIME_REVERSE:
        current_directory_list.sort(key=lambda element : element.date_time_object, reverse=True)    
    if sort_state == SortState.FILE_SIZE:
        current_directory_list.sort(key=lambda element : element.file_size_bytes)
    if sort_state == SortState.FILE_SIZE_REVERSE:
        current_directory_list.sort(key=lambda element : element.file_size_bytes, reverse=True)   

def on_select_all():
    for file in filtered_current_directory_list:
        file.select()

def on_unselect_all(only_filtered_files=False):
    if only_filtered_files == True:
        for file in filtered_current_directory_list:
            file.deselect()
    else:
        for file in current_directory_list:
            file.deselect()
        selected_files.clear()

# Path quoting explained at the top of this file.
def quote_path_correctly_outer_double_inner_single(path):
    return path.replace("'", "'\\''").replace("\"", "\\\"").replace("$", "\\$").replace("`", "\\`")

def quote_path_correctly_outer_double(path):
    return path.replace("\"", "\\\"").replace("$", "\\$").replace("`", "\\`")
##

def scroll_to_top():
    global current_directory_list_index
    current_directory_list_index = 0
    # Arrowing down and up will correctly set the states of the up and down arrow.
    on_arrow_down()
    on_arrow_up()

# Removes any up or down arrows in the sorting button text
def set_default_sort_button_names():
    file_name_sort_button.config(text=FILE_NAME_SORT_BUTTON_STRING)
    date_time_sort_button.config(text=DATE_TIME_SORT_BUTTON_STRING)
    file_size_sort_button.config(text=FILE_SIZE_SORT_BUTTON_STRING)

####################
# Button Click Functions            

# Toggles a file's selection status
# Will highlight the file's label if applicable,
# Will toggle button states as applicable (interactions with files can only happen if at least 1 file is selected)
def on_file_select_toggle(file_descriptor, file_name_label):
    file_descriptor.is_selected = not file_descriptor.is_selected

    if file_descriptor.is_selected == True:
        try:
            file_name_label.config(bg="blue")
        except:
            pass
        selected_files.add(file_descriptor)
        modify_widget_states(enable_list=[pull_button, open_button, move_button, delete_button])
    else:
        try:
            file_name_label.config(bg="light gray")
        except:
            pass
        try:
            selected_files.remove(file_descriptor)
        except:
            pass
        if len(selected_files) == 0:
            modify_widget_states(disable_list=[pull_button, open_button, move_button, delete_button])

# Increases the current_directory_list_index if necessary.
# Arrow down button should only be clickable if there are more files out of view.
def on_arrow_down():
    global current_directory_list_index

    def set_correct_button_state():
        if current_directory_list_index + MAX_LIST_LENGTH > len(filtered_current_directory_list):
            modify_widget_states(disable_list=[file_scrolldown_button])
            return False
        else:
            modify_widget_states(enable_list=[file_scrolldown_button])
            return True

    # If there exists more files out of view...
    if set_correct_button_state() == True:
        # Increase the index by 1 to get the next file
        current_directory_list_index = current_directory_list_index + 1
        # By increasing the index, we have now scrolled down, so the scroll up button must be enabled
        modify_widget_states(enable_list=[file_scrollup_button])
        # re-run the check, which will then disable the scroll down button if we have now scrolled as far as possible.
        set_correct_button_state()
        display_file_list()

# Decreases the current_directory_list_index if necessary.
# Arrow up button should only be clickable if the index is greater than 0
def on_arrow_up():
    global current_directory_list_index

    def set_correct_button_state():
        if current_directory_list_index == 0:
            modify_widget_states(disable_list=[file_scrollup_button])
            return False
        else:
            modify_widget_states(enable_list=[file_scrollup_button])
            return True

    # If there exists more files out of view...
    if set_correct_button_state() == True:
        # Decrease the index by 1 to get the next file
        current_directory_list_index = current_directory_list_index - 1
        # By decreasing the index, we have now scrolled up, so the scroll down button must be enabled
        modify_widget_states(enable_list=[file_scrolldown_button])
        # re-run the check, which will then disable the scroll up button if we have now scrolled as far as possible.
        set_correct_button_state()
        display_file_list()

# Updates the file name sort button
def on_file_name_sort():
    global sort_state

    set_default_sort_button_names()

    # If already sorting as A-Z or Z-A, flip it around
    if sort_state == SortState.ALPHA:
        sort_state = SortState.ALPHA_REVERSE
        file_name_sort_button.config(text=FILE_NAME_SORT_BUTTON_STRING + " " + DOWN_ARROW_STRING)
    # Else set to A-Z
    else:
        sort_state = SortState.ALPHA
        file_name_sort_button.config(text=FILE_NAME_SORT_BUTTON_STRING + " " + UP_ARROW_STRING)

    redraw()

# Updates the date time sort button
def on_date_time_sort():
    global sort_state

    set_default_sort_button_names()

    # If already sorting as oldest to newest or newest to oldest, flip it around
    if sort_state == SortState.DATE_TIME:
        sort_state = SortState.DATE_TIME_REVERSE
        date_time_sort_button.config(text=DATE_TIME_SORT_BUTTON_STRING + " " + DOWN_ARROW_STRING)
    # Else set to oldest to newest
    else:
        sort_state = SortState.DATE_TIME
        date_time_sort_button.config(text=DATE_TIME_SORT_BUTTON_STRING + " " + UP_ARROW_STRING)

    redraw()

# Updates the file size sort button
def on_file_size_sort():
    global sort_state

    set_default_sort_button_names()

    # If already sorting as 0-N or N-0, flip it around
    if sort_state == SortState.FILE_SIZE:
        sort_state = SortState.FILE_SIZE_REVERSE
        file_size_sort_button.config(text=FILE_SIZE_SORT_BUTTON_STRING + " " + DOWN_ARROW_STRING)
    # Else set 0-N
    else:
        sort_state = SortState.FILE_SIZE
        file_size_sort_button.config(text=FILE_SIZE_SORT_BUTTON_STRING + " " + UP_ARROW_STRING)

    redraw()

# If all files are selected, unselect all, else select all.
def on_select_or_clear_all():
    selection_required = False

    for filtered_file in filtered_current_directory_list:
        if filtered_file not in selected_files:
            selection_required = True
            break

    if selection_required == True:
        on_select_all()
    else:
        on_unselect_all(True)

# Changes directory, and then refreshes the view (which will query the file system etc etc)
def on_directory_clicked(file_descriptor):
    global current_directory_value
    global current_directory_list_index
    result = subprocess.run(GET_TARGET_DIRECTORY_PATH.format(absolute_directory=quote_path_correctly_outer_double_inner_single(current_directory_value + file_descriptor.file_name)), shell=True, capture_output=True, text=True)
    current_directory_value = result.stdout.rstrip()
    current_directory_field.delete(1.0, tkinter.END)
    current_directory_field.insert(tkinter.END, current_directory_value)
    current_directory_list_index = 0
    refresh()
    # After a refresh, all selections will be cleared out which will disable all interaction buttons including the move button
    # But if we are in a move state, then the move button must remain enabled.
    if move_state_info_object is not None:
        modify_widget_states(enable_list=[move_button])

# Filters the list of known files. Does not do a new query.
def on_search():
    global search_file_field_value
    search_file_field_value = search_file_field.get("1.0", tkinter.END).rstrip()    
    scroll_to_top()
    display_file_list()
    scroll_to_top()

# Creates a new directory in the current directory
def on_create_directory():
    new_directory_name = create_directory_field.get("1.0", tkinter.END).rstrip().split("/")[0]
    command = CREATE_DIRECTORY_COMMAND.format(absolute_directory=quote_path_correctly_outer_double_inner_single(current_directory_value + new_directory_name))
    subprocess.run(command, shell=True)
    print("Command run: {command}".format(command=command))
    create_directory_field.delete(1.0, tkinter.END)
    refresh()

# Pulls every selected file to the host computer
# If a directory is selected, the directory structure is created on the host computer first, 
# and then files are are pulled into that structure appropriately
def on_pull():
    file_pull_list = []

    # If the file is not a directory, then no special processing is required.
    for file in selected_files:
        if file.is_directory == False:
            file_pull_list.append(file)
        # Else, get all files in this directory
        else:
            command = GET_ALL_FILES_IN_DIRECTORY_RECURSIVELY_COMMAND.format(absolute_directory=quote_path_correctly_outer_double_inner_single(current_directory_value + file.file_name + "/"))
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            print("Command run: {command}".format(command=command))
            sub_file_list = filter_empty_string_elements(result.stdout.split("\n"))
            for sub_file in sub_file_list:
                # e.g. "/sdcard/TestDirectory/test.txt" -> ["sdcard", "TestDirectory", "test.txt"]
                sub_file_path_list = filter_empty_string_elements(sub_file.split("/"))
                # ["sdcard", "TestDirectory", "test.txt"] -> "test.txt"
                sub_file_name = sub_file_path_list[-1]
                # ["sdcard", "TestDirectory", "test.txt"] -> "/sdcard/TestDirectory/"
                sub_file_absolute_directory_path = "/" + '/'.join(sub_file_path_list[:-1]) + "/"
                sub_file_descriptor = FileDescriptor(False, sub_file_name, sub_file_absolute_directory_path, "1970-01-01 00:00", 0)
                file_pull_list.append(sub_file_descriptor)

    # For each identified file that has been selected directly or indirectly...
    for file in file_pull_list:
        # Choose the name of the file that will be used on the host computer
        file_name_on_host = file.file_name if CURRENT_OS != "Windows" else file.file_name_compat

        # If the file is not in the current directory path, then it must be inside one of the selected directories...
        # Which means the directory structure will need to be created on the host first
        if file.file_absolute_directory_path != current_directory_value:
            # e.g. "/sdcard/TestDirectory" -> "TestDirectory/"
            new_host_directory_path = file.file_absolute_directory_path.replace(current_directory_value, "")
            # ["TestDirectory"]
            new_host_directory_path = filter_empty_string_elements(new_host_directory_path.split("/"))

            # If using Windows, compatible directory names must be used when creating the structure on the host.
            if CURRENT_OS == "Windows":
                for directory_name_index in range(0, len(new_host_directory_path)):
                    new_host_directory_path[directory_name_index] = get_compatibility_name(new_host_directory_path[directory_name_index])

            # e.g. ["TestDirectory"] -> /my_programs/adb_file_viewer/output/TestDirectory/
            new_host_directory_path = os.path.join(os.path.abspath("."), OUTPUT_FOLDER, *new_host_directory_path) + "/"
            os.makedirs(new_host_directory_path, exist_ok=True)
            # "test.txt" -> /my_programs/adb_file_viewer/TestDirectory/test.txt
            absolute_file_path_on_host = new_host_directory_path + file_name_on_host
        else:
            absolute_file_path_on_host = os.path.join(os.path.abspath("."), OUTPUT_FOLDER, file_name_on_host)

        command = PULL_FILE_COMMAND.format(absolute_file_path=quote_path_correctly_outer_double(file.file_absolute_directory_path + file.file_name), absolute_file_path_on_host=quote_path_correctly_outer_double(absolute_file_path_on_host))
        subprocess.run(command, shell=True)
        print("Command run: {command}".format(command=command))

# Runs pull first, and then opens up each selected file
# If a directory has been selected, the directory will be opened, but not the files within it.
def on_open():
    on_pull()
    for file in selected_files:
        correct_file_name = file.file_name if CURRENT_OS != "Windows" else file.file_name_compat
        absolute_file_path_on_host = os.path.join(os.path.abspath("."), OUTPUT_FOLDER, correct_file_name)
        command = RUNTIME_OPEN_COMMAND.format(absolute_file_path_on_host=quote_path_correctly_outer_double(absolute_file_path_on_host))
        subprocess.run(command, shell=True)
        print("Command run: {command}".format(command=command))
        
# For each selected file, delete it on the file system. 
def on_delete():
    for file in selected_files:
        command = DELETE_COMMAND.format(absolute_file_path=quote_path_correctly_outer_double_inner_single(current_directory_value + file.file_name))
        subprocess.run(command, shell=True)
        print("Command run: {command}".format(command=command))
    refresh()

# After selecting some files, it is possible to use the move functionality
# When clicking the move button initially, the program enters the move state, and the file view changes to only show directories
# ALl other buttons except the move button are disabled.
# It is possible to navigate into different directories before finally moving the files
# When the move button is clicked a second time, if the directory has not changed, the move state is toggled off as no move is required...
# Selected files remain selected, and a move can be attempted again. All buttons are enabled.
# Else, if the program is in a different directory, all selected files are moved and then the view is refreshed.
def on_move():
    global move_state_info_object
    # Initial move button click...
    if move_state_info_object is None:
        # Save the current directory, which will be used when the actual move is done
        # as the program will be in a different directory when the move occurs
        move_state_info_object = MoveStateInfo(current_directory_value, selected_files)
        scroll_to_top()
        display_file_list()
        scroll_to_top()
        modify_widget_states(disable_list=[refresh_button, create_directory_button, pull_button, open_button, delete_button])
    else:
        # Move button clicked again but in the same directory...
        if move_state_info_object.initial_working_directory == current_directory_value:
            for file in current_directory_list:
                if file.file_name in move_state_info_object.file_names:
                    file.select()
            move_state_info_object = None
            display_file_list()
            modify_widget_states(enable_list=[refresh_button, create_directory_button, pull_button, open_button, delete_button])
        else:
            # Move button clicked again, different directory
            for file_name in move_state_info_object.file_names:
                command = MOVE_COMMAND.format(absolute_file_path=quote_path_correctly_outer_double_inner_single(move_state_info_object.initial_working_directory + file_name), absolute_directory=current_directory_value)
                subprocess.run(command, shell=True)
                print("Command run: {command}".format(command=command))
            move_state_info_object = None
            refresh()
            modify_widget_states(enable_list=[refresh_button, create_directory_button], disable_list=[pull_button, open_button, move_button, delete_button])

create_toolbar()
create_separator()
create_sort_bar()
create_separator()

root.bind("<Button-4>", lambda event : file_scrollup_button.invoke())
root.bind("<Button-5>", lambda event : file_scrolldown_button.invoke())
root.mainloop()