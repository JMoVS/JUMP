"""This is the main component and main class which runs"""

__copyright__ = "Copyright 2015 - 2017, Justin Scholz"
__author__ = "Justin Scholz"

import sys, os
import time

import pickle
import DataStorage
from MeasurementComponents import Measurement
import UserInput

from _version import __version__



class MeasurementProgram:

    def __init__(self):
        self.operator = "Tron"
        self.working_directory = "C:\Data\Tron\Run1"
        self.general_info_acquired = False

    def start(self):
        UserInput.post_status("Welcome to JUMP, Justin's Universal Measurement Program, the savory pill to satisfy your measurement needs!")

        should_run = True

        while should_run:

            question = {"question_title": "Current mode",
                        "question_text": "What do you want to do?",
                        "default_answer": 1,
                        "optiontype": "multi_choice",
                        "valid_options": ["create a new measurement (eg a sweep or a full-blown measurement)",
                                          "Load a previously generated .JUMP-file and work with the data",
                                          "exit the program"]}

            answer = UserInput.ask_user_for_input(question)["answer"]

            if answer == 0:
                if not self.general_info_acquired:
                    self._general_info()
                self.measure()
            elif answer == 1:
                self.work_with_db()
            elif answer == 2:
                UserInput.post_status("I say Goodbye and I hope to see you soon!")
                should_run = False

    def _general_info(self):

        question = {"question_title": "Name of Operator",
                "question_text": "What is the name of the operator?",
                "default_answer": "Tron",
                "optiontype": "free_text"}

        self.operator = UserInput.ask_user_for_input(question)["answer"]
        default_path = "C:\Data\JUMP" + os.sep + self.operator
        question = {"question_title": "Working directory",
                "question_text": "Please choose a working directory for the following session with this program",
                "default_answer": default_path,
                "optiontype": "free_text"}

        self.working_directory = UserInput.ask_user_for_input(question)["answer"] + os.sep
        if not os.path.isdir(self.working_directory):
            os.makedirs(self.working_directory)

        question = {"question_title": "Room",
                "question_text": "In what room are you operating?",
                "default_answer": "Dark laboratory",
                "optiontype": "free_text"}

        self.room = UserInput.ask_user_for_input(question)["answer"]

        self.general_info_acquired = True

    def work_with_db(self):
        unpickled_db = None # type: DataStorage.Database
        full_path = None # type: str
        user_didnt_manage_to_open_db = True

        while user_didnt_manage_to_open_db:
            question = {"question_title": "Path to db",
                        "question_text": "Please enter the path to the folder containing the database (database's file "
                                         "name shall be the same as the folder) or provide the full path incuding the"
                                         " file name.",
                        "default_answer": self.working_directory,
                        "optiontype": "free_text"}
            full_path = UserInput.ask_user_for_input(question)["answer"]  # type: str
            full_path = full_path.replace("\"", "")

            # We first check whether the user provided us with a full path including the file name. We first split it folder
            # path + file name at the ".". If that shows up empty (because you copied the path from explorer without the
            # file name), we will then split at the last path component and attempt to open the database with the last path
            # component.JUMP
            path_split_to_filename = full_path.rpartition(".")
            # Only valid if the user didn't include the file name
            if path_split_to_filename[0] == "":
                path_last_folder_split = full_path.rpartition(os.sep)
                file_name = path_last_folder_split[2] + ".JUMP"
                full_path = full_path + os.sep + file_name

            try:
                with open(full_path, 'rb') as incoming:
                    unpickled_db = pickle.load(incoming)  # type: DataStorage.Database
                user_didnt_manage_to_open_db = False
            except FileNotFoundError:
                UserInput.confirm_warning("A database wasn't found at {0}. Please provide a full path including the "
                                          "file name or rename the database on disk so that the file name is the same "
                                          "as the folder and the extension is '.JUMP.'".format(full_path))
                user_didnt_manage_to_open_db = True

        DataStorage.main_db.change_to_passed_db(unpickled_db)
        DataStorage.main_db.start_post_processing(full_path)

    def measure(self):

        question = {"question_title": "Name for run",
                "question_text": "What shall this run be named? (This will be the folder and file name)",
                "default_answer": "Run1",
                "optiontype": "free_text"}

        name_for_run = UserInput.ask_user_for_input(question)["answer"]

        run_directory = self.working_directory + name_for_run + os.sep

        question = {"question_title": "Comment for run",
                "question_text": "Do you want to add a comment to this file?",
                "default_answer": "I fight for the User!",
                "optiontype": "free_text"}

        comment = UserInput.ask_user_for_input(question)["answer"]

        # Prepare the database for the run
        DataStorage.main_db.start_fresh(name_for_run, run_directory, self.operator, self.room, comment,
                                        time.strftime("%d.%m.%Y %H:%M:%S"))
        
        meas = Measurement()

        user_wants_something = True
        question = {"question_title": "Choose template",
                    "question_text": "Choose wether you want to start a custom measurement or use a template instead",
                    "default_answer": "Custom",
                    "optiontype": "multi_choice",
                    "valid_options": ["Custom","S001"]}
        
        chosen_template = UserInput.ask_user_for_input(question)["answer"]
        
        if chosen_template==0:
            while user_wants_something:
    
                question = {"question_title": "Task Management",
                            "question_text": "Do you want to add or remove the task or start the measurement?",
                            "default_answer": 0,
                            "optiontype": "multi_choice",
                            "valid_options": ["+ Add a task", "- remove a task", "|> start the measurement!"]}
                user_wants = UserInput.ask_user_for_input(question)["answer"]
    
                if user_wants == 0:     # User wants to add a task
                    user_wants_something = True
                    meas.new_task()
    
                elif user_wants == 1:
                    user_wants_something = True
                    meas.remove_task()
    
                else:
                    user_wants_something = False
    
                meas.print_current_task_list()
        elif chosen_template==1:
            meas.new_task(False,[2,0,1.0,3.0])
            #meas.new_task(False,[2,0,1.0,3.0])
            #meas.new_task(False,[1,'ND_Max',False])
            #meas.new_task(False,[2,0,1.0,3.0])
            #meas.new_task(False,[2,0,1.0,3.0])
            question = {"question_title": "Total time",
                            "question_text": "Please enter the total time of the measurement in minutes",
                            "default_answer": 10.0,
                            "optiontype": "free_choice",
                            "valid_options_lower_limit": 0.0,
                            "valid_options_upper_limit": 1e64,
                            "valid_options_steplength": 1e16}
            answer_time_total = UserInput.ask_user_for_input(question)
            question = {"question_title": "Trigger separation",
                            "question_text": "Please enter the trigger separation in minutes. "
                                             "Eg every 3 minutes",
                            "default_answer": 3.0,
                            "optiontype": "free_choice",
                            "valid_options_lower_limit": 0.0,
                            "valid_options_upper_limit": 1e64,
                            "valid_options_steplength": 1e16}
            answer_trigger_seperation = UserInput.ask_user_for_input(question)
            meas.new_task(False,[2,0,answer_time_total["answer"],answer_trigger_seperation["answer"],1])
            meas.new_task(False,[1,0,False,1])
            
            
            meas.print_current_task_list()
    
        meas.measure()
        # Instruct database to be pickled
        DataStorage.main_db.measurement_finished()


def version():
    """
        simply prints the current version
    """
    print(__version__)

if "version" in sys.argv:
    version()
MP = MeasurementProgram()

MP.start()