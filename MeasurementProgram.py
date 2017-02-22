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
        self.working_directory = ""
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
        question = {"question_title": "Full path to db",
                    "question_text": "Please enter the full path including file name for the database",
                    "default_answer": "C:\Data\JUMP\Justin\my_run.JUMP",
                    "optiontype": "free_text"}
        full_path = UserInput.ask_user_for_input(question)["answer"]

        with open(full_path, 'rb') as incoming:
            unpickled_db = pickle.load(incoming)  # type: DataStorage.Database

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
