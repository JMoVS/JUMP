"""Provides a convenient way to store all data into first and foremost raw files and also into a datastore so the
data can be analyzed and displayed on screen"""
__copyright__ = "Copyright 2015 - 2017, Justin Scholz"
__author__ = "Justin Scholz"

import cmath
import pickle
import copy
import time
import queue
from threading import Thread
import os
import math

import UserInput
import _version


class Database:
    def __init__(self, name="Run1", pickle_path=".{0}".format(os.sep), experimenter="Tron", room="Dream World",
                 comment="I fight for the User!", creation_time=time.strftime("%d.%m.%Y %H:%M:%S")):
        self.db = {}  # {p1:[point1, point2], c1:[point1, point2]}
        self.tasks_of_a_run = []  # this is where we store the task list for a run
        self.name = name
        self.experimenter = experimenter
        self.room = room
        self.comment = comment
        self.pickle_path = pickle_path
        self.creation_time = creation_time
        self.version = _version.__version__
        self.task_input=[]#Helps with setting up a template

    def change_to_passed_db(self, unpickled_db):
        """

        :param unpickled_db:
        """
        self.db = unpickled_db.db
        self.tasks_of_a_run = unpickled_db.tasks_of_a_run

        try:
            self.name = unpickled_db.name
        except AttributeError:
            self.name = "Run1"

        try:
            self.pickle_path = unpickled_db.pickle_path
        except AttributeError:
            self.pickle_path = ".{0}".format(os.sep)

        try:
            self.version = unpickled_db.version
        except AttributeError:
            self.version = "0"

        try:
            self.experimenter = unpickled_db.experimenter
        except AttributeError:
            self.experimenter = "Tron"

        try:
            self.room = unpickled_db.room
        except AttributeError:
            self.room = "Dream World"

        try:
            self.comment = unpickled_db.comment
        except AttributeError:
            self.comment = "I fight for the User!"

    def start_fresh(self, name="Run1", pickle_path=".{0}".format(os.sep), experimenter="Tron", room="Dream World",
                 comment="I fight for the User!", creation_time=time.strftime("%d.%m.%Y %H:%M:%S")):
        """ You may want to make multiple measurement runs. This means though that the database should be cleared. This
        wipes all data and starts clean.

        :param pickle_path:
        :param name:
        """
        self.db = {}
        self.tasks_of_a_run = []
        self.name = name
        self.pickle_path = pickle_path
        self.version = _version.__version__
        self.experimenter = experimenter
        self.room = room
        self.comment = comment
        self.creation_time = creation_time

    def measurement_finished(self):
        # Database should be pickled NOW
        self.pickle_database()

    def pickle_database(self, suffix=""):
        if not os.path.isdir(self.pickle_path):
            os.makedirs(self.pickle_path)
        filename = "{0}{1}{2}{3}.JUMP".format(self.pickle_path, os.sep, self.name, suffix)
        with open(filename, 'wb') as output:
            pickle.dump(self, output, -1)

    def new_pickle_path(self, new_pickle_path:str):
        if not new_pickle_path.endswith(os.sep):
            new_pickle_path += os.sep
        self.pickle_path = new_pickle_path

    def start_post_processing(self, path_to_opened_db:str):
        database_to_manipulate = copy.deepcopy(self)  # type: Database
        path = os.path.dirname(path_to_opened_db)
        if database_to_manipulate.pickle_path == ".{0}".format(os.sep):
            database_to_manipulate.pickle_path = os.getcwd() + os.sep

        #TODO: Consider more useful path display
        question = {"question_title": "Output directory",
                    "question_text": "The current output directory is '{0}' . "
                                     "Do you want to change it?".format(path),
                    "default_answer": True,
                    "optiontype": "yes_no"}

        user_wants_to_change_path = UserInput.ask_user_for_input(question)["answer"]

        if user_wants_to_change_path:
            question = {"question_title": "Output directory",
                    "question_text": "Please enter a working directory for the following processing session.",
                    "default_answer": "C:\Data\JUMP",
                    "optiontype": "free_text"}

            new_path = UserInput.ask_user_for_input(question)["answer"]
            path = new_path

        database_to_manipulate.new_pickle_path(path)
        
        UserInput.post_status("")
        UserInput.post_status("-------------Choose template-------------")

        UserInput.post_status("Choose whether you want to customize your post-processing, or want to use an existing"
                              "template")
        
        question = {"question_title": "Choose template",
                    "question_text": "Please choose a template",
                    "default_answer": "Custom",
                    "optiontype": "multi_choice",
                    "valid_options": ["Custom","S001"]}
        
        chosen_template = UserInput.ask_user_for_input(question)["answer"]
        if chosen_template==0:
            database_to_manipulate._post_process(True)
        elif chosen_template==1:
            template=[False,False,True,[1,2],False,True,[0,1],False,[0],False,False,0]#TODO Testing
            database_to_manipulate._post_process(False,template)
        

    def _post_process(self, custom:bool=True,template=[]):
        """ the post processing workflow follows the steps outlined in post_processing_steps

        """
        template=template;
        
        
        post_processing_steps = ["1. Ask user whether he wants geometry based calculations and calculate all possible"
                                 " values",
                                 "2. Merge *all* <<same>> level datapoints/DataAcquisitions",
                                 "3. Merge *all* <<different>> level datapoints (usually ParamControllers or Triggers "
                                 "together with DataAcquisitions",
                                 "4. Integrate *all* <<multi-level>> tasks (temperature+frequencies)",
                                 "5. Specify first output list",
                                 "6. If needed, transpose datapoints (temp-> freq)",
                                 "7. Define file naming, header and columns for first list",
                                 "8. Define file naming, header and columns for second list",
                                 "9. Start file-output",
                                 "10. Be happy"]

        processing_log = []
        current_log_index = 0
        UserInput.post_status("You are now in post processing mode. You are post-processing the database: " + self.name)

        # ------ Helper methods for the post_processing_workflow

        def print_following_steps(start_index):
            """Little method to print the current + all following steps of the post-processing-workflow

            :param start_index:
            """
            UserInput.post_status("These are the steps to the finish line, starting with the current one:")
            for index, item in enumerate(post_processing_steps):
                if index >= start_index:
                    UserInput.post_status(item)

        def print_current_processing_log(start_index=0):
            """Little method to print the log of the processing workflow

            :param start_index:
            """
            for index, item in enumerate(processing_log):
                if index >= start_index:
                    UserInput.post_status(item)

        def print_task_list_with_indeces():
            for index, item in enumerate(self.tasks):
                UserInput.post_status(str(index) + ": " + item)

        def get_task_id_from_task_list_index(index_in_task_list):
            task = self.tasks[index_in_task_list]
            identifier_str = task.split("]")[0].split("[")[1].split(",")
            identifier = []
            for item in identifier_str:
                identifier.append(int(item))
            return identifier
        
        def setup_postprocessing():
            pass

        # -------------------------------------------------------------------------------------------------------------
        
       
        if True:
            # Step 1: Ask user whether he wants geometry based calculations and calculate all possible values
    
            print_following_steps(0)
    
            UserInput.post_status("")
            UserInput.post_status("-------------Step 1: Geometry-------------")
    
            UserInput.post_status("You now have the chance to enter a geometry so all the possible quantities can be "
                                  "calculated for you")
    
            question = {"question_title": "Sample geometry",
                        "question_text": "You can enter the sample geometry in mm (Millimeter!), do you want that?",
                        "default_answer": True,
                        "optiontype": "yes_no"}
    
            user_wants_geometry = self._get_input(custom, question, template)
    
            if user_wants_geometry:
                question = {"question_title": "Sample Thickness",
                            "question_text": "Please enter the sample's thickness in mm. Valid values range from 0 to "
                                             "9999999, maximum accuracy is capped at 0.0000001",
                            "default_answer": 1.0,
                            "optiontype": "free_choice",
                            "valid_options_lower_limit": 0.0,
                            "valid_options_upper_limit": 9999999,
                            "valid_options_steplength": 1e7}
    
                thickness = self._get_input(custom, question, template)
    
                question = {"question_title": "Sample area",
                            "question_text": "Please enter the sample's area in mm^2. Valid values range from 0 to 9999999,"
                                             " maximum accuracy is capped at 0.0000001",
                            "default_answer": 1.0,
                            "optiontype": "free_choice",
                            "valid_options_lower_limit": 0.0,
                            "valid_options_upper_limit": 9999999,
                            "valid_options_steplength": 1e7}
    
                area = self._get_input(custom, question, template)
                self.geometry = {"thickness": thickness,
                                 "area": area}
    
                UserInput.post_status("Successfully gathered the geometry info. All values will be calculated. This can "
                                      "take a moment.")
    
                processing_log.append(time.strftime("%c") + ": User entered geometry. Starting value calculation.")
                self.calculate_all_values(self.geometry)
                processing_log.append(time.strftime("%c") + ": All values calculated.")
    
            else:
                UserInput.post_status("Values will be calculated without geometry input, but calculation could nevertheless"
                                      " take a moment.")
    
                processing_log.append(time.strftime("%c") + ": User didn't enter geometry. Starting value calculation.")
                self.calculate_all_values()
                self.geometry = {"Info": "no geometry given"}
                processing_log.append(time.strftime("%c") + ": All values calculated.")
    
            UserInput.post_status("All values are now calculated. Successfully finished step 1. New step is step 2.")
    
            # -------------------------------------------------------------------------------------------------------------
            # Step 2: Merge *all* same level datapoints/DataAcquisitions
   
            UserInput.post_status("####################################")
            UserInput.post_status("-------------Step 2: Same level merge-------------")
    
            processing_log.append(time.strftime("%c") + ": Entering step 2")
    
            print_following_steps(1)
            current_log_index = len(processing_log) - 1
    
            UserInput.confirm_warning(
                "Now please merge all same-level tasks. Same level means that all but the very last index"
                " components may differ. For example: \n\n [0,0,0,0] and [0,0,0,1] can be merged. \n\n"
                "!!! [0,0,0] and [0,0,0,0] can't be merged in this step because that's a level 3 and "
                "a level 4 merge. \n"
                "!!! [0,0,0,0] and [1,0,0,0] can't be merged because they differ on the first index "
                "component. \n\n"
                "This merging process will only be needed in rare cases where you for example recorded "
                "both sample AND control temperature in DataAcquisitons or have additional sensors.",custom)
    
            step2_is_finished = False
    
            while not step2_is_finished:
                UserInput.post_status("°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°")
                UserInput.post_status("Processing log for step 2:")
                print_current_processing_log(current_log_index)
                UserInput.post_status("°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°")
    
                question = {"question_title": "Merge same level tasks",
                            "question_text": "Do you want to merge (another) two tasks?",
                            "default_answer": False,
                            "optiontype": "yes_no"}
    
                user_wants_new_merge = self._get_input(custom, question, template)
    
                if user_wants_new_merge:
                    print_task_list_with_indeces()
                    question = {"question_title": "Same-level-merge selection",
                                "question_text": "Please enter the two indeces, (you will get two input prompts) for the "
                                                 "two which are to be merged. The result is that the second one is "
                                                 "<<integrated>> into the <<first>> one.",
                                "default_answer": "0",
                                "optiontype": "2_indeces"}
                    index_list = self._get_input(custom, question, template)
    
                    identifier1 = get_task_id_from_task_list_index(index_list[0])
                    identifier2 = get_task_id_from_task_list_index(index_list[1])
    
                    self.merge_same_level_datapoints(identifier1, identifier2)
                    processing_log.append(time.strftime("%c") + ": Merged " + str(identifier2) + " into -> " +
                                          str(identifier1))
                else:
                    step2_is_finished = True
    
            # -------------------------------------------------------------------------------------------------------------
            # Step 3: Merge *all* different level datapoints/DataAcquisitions
            UserInput.post_status("####################################")
            UserInput.post_status("-------------Step 3: Different level merge-------------")
    
            processing_log.append(time.strftime("%c") + ": Entering step 3")
            # We are at step 3, which starting counting at 0 means we should print 2 going forward
            print_following_steps(2)
            current_log_index = len(processing_log) - 1
    
            UserInput.confirm_warning(
                "Now please merge all different-level tasks. Different level means that all compinents "
                "of the identifier are the same, just the second one has one more component. This process"
                " is almost always needed, if onyl to merge ParamController with DataAcquisitions",custom)
    
            step3_is_finished = False
    
            while not step3_is_finished:
                UserInput.post_status("°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°")
                UserInput.post_status("Processing log for step 3:")
                print_current_processing_log(current_log_index)
                UserInput.post_status("°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°")
    
                question = {"question_title": "Merge different level tasks",
                            "question_text": "Do you want to merge (another) two tasks?",
                            "default_answer": False,
                            "optiontype": "yes_no"}
    
                user_wants_new_merge = self._get_input(custom, question, template)
    
                if user_wants_new_merge:
                    print_task_list_with_indeces()
                    question = {"question_title": "Different-level-merge selection",
                                "question_text": "Please enter the two indeces, (you will get two input prompts) for the "
                                                 "two which are to be merged. The result is that the second one is "
                                                 "<<integrated>> into the <<first>> one.",
                                "default_answer": "0",
                                "optiontype": "2_indeces"}
                    index_list = self._get_input(custom, question, template)
    
                    identifier1 = get_task_id_from_task_list_index(index_list[0])
                    identifier2 = get_task_id_from_task_list_index(index_list[1])
    
                    self.merge_diff_level_datapoints(identifier1, identifier2)
                    processing_log.append(time.strftime("%c") + ": Merged " + str(identifier2) + " into -> " +
                                          str(identifier1))
    
                else:
                    step3_is_finished = True
    
            # -------------------------------------------------------------------------------------------------------------
            # Step 4: Integrate *all* multi-level connections (temperature+frequencies)
    
            UserInput.post_status("####################################")
            UserInput.post_status("-------------Step 4: Multi-level integration-------------")
    
            processing_log.append(time.strftime("%c") + ": Entering step 4")
    
            print_following_steps(3)
            current_log_index = len(processing_log) - 1
    
            UserInput.confirm_warning(
                "Now please integrate the tasks. This usually means integrating already merged sub_tasks."
                " (Same with merging, integrating means that tghe result will be in the first entered"
                " one). In a classical dielectric measurement, you usually have 30 frequencies at every "
                "temperature. This step integrate the 30 frequencies data into the temperature "
                "datapoints. This is the reason that the first task must contain equal or less "
                "datapoints than the second task.",custom)
    
            step4_is_finished = False
    
            while not step4_is_finished:
                UserInput.post_status("°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°")
                UserInput.post_status("Processing log for all steps:")
                print_current_processing_log(0)
                UserInput.post_status("°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°")
    
                question = {"question_title": "Integrate datarows",
                            "question_text": "Do you want to integrate (another) two tasks?",
                            "default_answer": False,
                            "optiontype": "yes_no"}
    
                user_wants_new_merge = self._get_input(custom, question, template)
    
                if user_wants_new_merge:
                    print_task_list_with_indeces()
                    question = {"question_title": "Same-level-merge selection",
                                "question_text": "Please enter the two indeces, (you will get two input prompts) for the "
                                                 "two which are to be merged. The result is that the second one is "
                                                 "<<integrated>> into the <<first>> one.",
                                "default_answer": "0",
                                "optiontype": "2_indeces"}
                    index_list = self._get_input(custom, question, template)
    
                    identifier1 = get_task_id_from_task_list_index(index_list[0])
                    identifier2 = get_task_id_from_task_list_index(index_list[1])
    
                    self.insert_sub_datapoints_into_parent_datapoint(identifier1, identifier2)
                    processing_log.append(time.strftime("%c") + ": Integrated " + str(identifier2) + " into -> "
                                          + str(identifier1))
    
                else:
                    step4_is_finished = True
    
            # -------------------------------------------------------------------------------------------------------------
            # Step 5: Specify first output list
    
            UserInput.post_status("-------------Step 5: Tasks for first output file-------------")
    
            processing_log.append(time.strftime("%c") + ": Entering step 5")
    
            print_following_steps(4)
            current_log_index = len(processing_log) - 1
    
            datapoint_list_1 = []
    
            UserInput.confirm_warning(
                "Now, specify the first round of now massaged tasks that you want output from. This is"
                "the first ouput round. As you can see, you can transpose the data as needed in step 6. "
                "In step 8, you'll be able to configure how exactly they should be printed out into "
                "the file.",custom)
            print_task_list_with_indeces()
    
            question = {"question_title": "First output selection",
                        "question_text": "Please enter one or more indeces separated only by a comma to be "
                                         "selected for file-output",
                        "default_answer": "0,4,8,12",
                        "optiontype": "multi_indeces"}
    
            indeces = self._get_input(custom, question, template)
    
            processing_log.append(time.strftime("%c") + ": Selected tasks at indeces :" + str(indeces) + " for output 1")
    
            for index in indeces:
                task_identifier = get_task_id_from_task_list_index(index)
                linked_datapoints = self._get_datapoint_list_at_identifier(task_identifier)
                copied_datapoints = copy.deepcopy(linked_datapoints)
                datapoint_list_1.append(copied_datapoints)
    
            # -------------------------------------------------------------------------------------------------------------
            # Step 6: If needed, transpose datapoints (temp-> freq) (automatically selected for output in second list)
    
            UserInput.post_status("-------------Step 6: Optionally transpose datapoints-------------")
    
            processing_log.append(time.strftime("%c") + ": Entering step 6")
    
            user_wants_transposed = False
    
            print_following_steps(5)
            current_log_index = len(processing_log) - 1
    
            datapoint_list_2 = []
    
            UserInput.confirm_warning("This step is to make it easy to also get your data into files in the other "
                                      "dependency. You essentially transpose the result matrix. In other terms, you are "
                                      "able to output per frequency and not just per temperature.",custom)
    
            question = {"question_title": "Do you want transposed data?",
                        "question_text": "In a sweep, you won't, in a regular measurementa, you almost surely will.",
                        "default_answer": True,
                        "optiontype": "yes_no"}
    
            user_wants_transposed = self._get_input(custom, question, template)
    
            if user_wants_transposed:
    
                UserInput.post_status("Here comes a nice time saver! Beware!")
                question = {"question_title": "Use tasks selected in step 5?",
                            "question_text": "Usually/Always, you want just the tasks you merged, integrated and selected for "
                                             "file output to also be transposed so you get the temperature dependency as well. "
                                             "If you select yes, the previously selected tasks will be the ones for output "
                                             "here.",
                            "default_answer": True,
                            "optiontype": "yes_no"}
    
                user_wants_tasks_from_step5 = self._get_input(custom, question, template)
    
                if user_wants_tasks_from_step5:
                    processing_log.append(time.strftime("%c") + ": Selected same tasks as in step 5 for file output 2.")
    
                elif not user_wants_tasks_from_step5:
    
                    question = {"question_title": "Second output selection",
                                "question_text": "Please enter one or more indeces separated only by a comma to be "
                                                 "selected for file-output. Everything you select is automatically "
                                                 "selected for 2nd file output.",
                                "default_answer": "0,4,8,12",
                                "optiontype": "multi_indeces"}
    
                    indeces = self._get_input(custom, question, template)
    
                    processing_log.append(time.strftime("%c") + ": Selected tasks at indeces :" + str(indeces) +
                                          " for output 2")
    
                # Add the datapoints to the output list 2
                for index in indeces:
                    task_identifier = get_task_id_from_task_list_index(index)
                    datapoint_list_2.append(self.get_transposed_parent_child_datapoints(task_identifier))
    
            # -------------------------------------------------------------------------------------------------------------
            # Step 7: Define file naming, header and columns for first list
            UserInput.post_status("####################################")
            UserInput.post_status("-------------1st OutputFile: Define file naming, header-------------")
    
            processing_log.append(time.strftime("%c") + ": Entering step 7")
    
            print_following_steps(6)
            current_log_index = len(processing_log) - 1
    
            directory_name = ""
    
            UserInput.confirm_warning("Now to the easier of the two lists. The first one is usually the one where you"
                                      "create one file per temperature.",custom)
    
            question = {"question_title": "Directory name",
                        "question_text": "Usually you want the directory named \"Temperatures\", do you want to use the "
                                         "default?",
                        "default_answer": True,
                        "optiontype": "yes_no"}
            user_is_fine_with_temperatures = self._get_input(custom, question, template)
            if user_is_fine_with_temperatures:
                directory_name = os.path.join(self.pickle_path, "Temperatures{0}".format(os.sep))
    
            elif not user_is_fine_with_temperatures:
                question = {"question_title": "name for directory",
                            "question_text": "Please choose a working directory for output of list 1",
                            "default_answer": "Temperatures",
                            "optiontype": "free_text"}
    
                directory_name = UserInput.ask_user_for_input(question)["answer"]
                directory_name = os.path.join(self.pickle_path, directory_name + os.sep)
    
            file_handler_1 = FileHandler(directory_name)
    
            file_number = 1
            file_number_str = "%05d" % (file_number,)  # we want leading 0s in the file name so file explorers sort them
            # correctly
            
    
            # Now iterate over all main tasks in the list:
    
            for number, main_task in enumerate(datapoint_list_1):
    
                # We need to ask the user what he wants as the base name for the files. For this, we show the user the top level
                #  descriptors that are available, eg "Sample Sensor"
    
                main_task_keys_without_subtasks = []
                UserInput.post_status("-----------------------")
                UserInput.post_status(
                    "At task {0}, what do you want as the attribute used inside the file name?".format(number))
                key_for_file_name = None
                for key in main_task[0].keys():
                    if key != "sub_task_datapoints":
                        main_task_keys_without_subtasks.append(key)
    
                main_task_keys_without_subtasks.sort()
    
                # Now ask the user which of the keys's value he wants to see in the file name
                for index, key in enumerate(main_task_keys_without_subtasks):
                    UserInput.post_status(str(index) + ": " + key)
    
                question = {"question_title": "What attributes' values should be used to put in the file name?",
                                "question_text": "Please only enter the 1 corresponding number",
                                "default_answer": "0",
                                "optiontype": "multi_indeces"}
    
                index_chosen = self._get_input(custom, question, template)
                key_for_file_name = main_task_keys_without_subtasks[index_chosen]
    
                keys_for_sub_task_datapoints = []
                # I want all keys that are in sub_task datapoints in a list so I can more easily work with them
                for key in main_task[0]["sub_task_datapoints"][0].keys():
                    keys_for_sub_task_datapoints.append(key)
    
                keys_for_sub_task_datapoints.sort(key=str.lower)
                # File Header
    
                first_line = ""
                for key in keys_for_sub_task_datapoints:
                    first_line = first_line + str(key) + "\t"
    
                second_line = "Name: " + self.name
                third_line = "Operator: " + self.experimenter + "\t"
                fourth_line = "Created at: " + self.creation_time
                fifth_line = "Comment: " + str(self.comment)
                sixth_line = "Geometry: " + str(self.geometry)
                seventh_line = "-------------------------------------------------------\n"
                nineth_line = seventh_line
                header_lines = [first_line, second_line, third_line, fourth_line, fifth_line, sixth_line, seventh_line]
    
    
                # Now we access each datarow we have
                for main_task_data_point in main_task:
    
                    processing_log.append(time.strftime("%c") + ": Processing task {0}".format(str(number)))
    
                    # now we have a dictionary at hand of our datapoints and each datapoint of the main_task gets its
                    # own file
                    file_name = "{0}_Task{1}_{2}_{3}".format(self.name, str(number), file_number_str,
                                                             str(main_task_data_point[key_for_file_name]))
    
                    # We need to count up the file number and ready the str of it
                    file_number += 1
                    file_number_str = "%05d" % (
                    file_number,)  # we want leading 0s in the name so file explorers sort them correctly
    
                    outputfile = file_handler_1.create_file(file_name)
    
                    # Write the header
                    for line in header_lines:
                        outputfile.write_string(line)
    
                    # Write main task datapoint data
                    main_task_data_str = ""
                    for key in main_task_keys_without_subtasks:
                        main_task_data_str += "\t{0} {1}".format(str(key), str(main_task_data_point[key]))
    
                    outputfile.write_string(main_task_data_str)
    
                    outputfile.write_string(nineth_line)
    
                    # now gather every sub_task_datapoint (one line in the output file)
                    for sub_task_datapoint in main_task_data_point["sub_task_datapoints"]:
                        line_of_data = ""
                        # then iterate over every key so we can generate the one line
                        for key in keys_for_sub_task_datapoints:
                            line_of_data += "{0}\t".format(sub_task_datapoint[key])
                        outputfile.write_string(line_of_data)
    
            UserInput.post_status("Export is in progress. You should shortly see the files appearing.")
    
            # -------------------------------------------------------------------------------------------------------------
            # Step 8: Define file naming, header and columns for second list
    
            if user_wants_transposed:
                UserInput.post_status("####################################")
                UserInput.post_status("-------------2nd OutputFile: Define file naming, header and columns-------------")
    
                processing_log.append(time.strftime("%c") + ": Entering step 8")
    
                print_following_steps(7)
                current_log_index = len(processing_log) - 1
    
                directory_name = ""
    
                UserInput.confirm_warning("Now to the hard part. The second list. This is the list containing your transposed "
                                          "entries, so in Dielectrics parlance, the frequency files.",custom)
    
                question = {"question_title": "Directory name",
                            "question_text": "Usually you want the directory named \"Frequencies\", do you want to use the "
                                             "default?",
                            "default_answer": True,
                            "optiontype": "yes_no"}
                user_is_fine_with_temperatures = self._get_input(custom, question, template)
                if user_is_fine_with_temperatures:
                    directory_name = os.path.join(self.pickle_path, "Frequencies{0}".format(os.sep))
    
                elif not user_is_fine_with_temperatures:
                    question = {"question_title": "name for directory",
                                "question_text": "Please choose a working directory for output of the list containing your "
                                                 "transposed task data",
                                "default_answer": "Frequencies",
                                "optiontype": "free_text"}
    
                    directory_name = self._get_input(custom, question, template)
                    directory_name = os.path.join(self.pickle_path, directory_name + os.sep)
    
                file_handler_2 = FileHandler(directory_name)
                # File Number for list 2 is 0 at the beginning of course
                file_number = 1
                file_number_str = "%05d" % (file_number,)  # we want leading 0s in the file name so file explorers sort them
                # correctly
    
                # Now iterate over all main tasks in the list:
    
                for number, main_task in enumerate(datapoint_list_2):
    
                    # We need to ask the user what he wants as the base name for the files. For this, we show the user the top level
                    #  descriptors that are available, eg "Sample Sensor"
    
                    main_task_keys_without_subtasks = []
    
                    UserInput.post_status("-----------------------")
                    UserInput.post_status(
                        "At task {0}, what do you want as the attribute used inside the file name?".format(number))
                    key_for_file_name = None
                    for key in main_task[0].keys():
                        if key != "sub_task_datapoints":
                            main_task_keys_without_subtasks.append(key)
    
                    main_task_keys_without_subtasks.sort()
    
                    # Now ask the user which of the keys's value he wants to see in the file name
                    for index, key in enumerate(main_task_keys_without_subtasks):
                        UserInput.post_status(str(index) + ": " + key)
    
                    question = {"question_title": "File name",
                                    "question_text": "What attributes' values should be used to put in the file name? Please "
                                                     "only enter the 1 corresponding number",
                                    "default_answer": "0",
                                    "optiontype": "multi_indeces"}
    
                    index_chosen = self._get_input(custom, question, template)
                    key_for_file_name = main_task_keys_without_subtasks[index_chosen]
    
                    keys_for_sub_task_datapoints = []
                    # I want all keys that are in sub_task datapoints in a list so I can more easily work with them
                    for key in main_task[0]["sub_task_datapoints"][0].keys():
                        # In the transposed case, we will have another set of sub_tasks that we don't want
                        if key != "sub_task_datapoints":
                            keys_for_sub_task_datapoints.append(key)
    
                    keys_for_sub_task_datapoints.sort(key=str.lower)
                    # File Header
    
                    first_line = ""
                    for key in keys_for_sub_task_datapoints:
                        first_line = first_line + str(key) + "\t"
    
                    second_line = "Name: " + self.name
                    third_line = self.experimenter + "\t"
                    fourth_line = "Created at: " + self.creation_time
                    fifth_line = "Comment: " + str(self.comment)
                    sixth_line = "Geometry: " + str(self.geometry)
                    seventh_line = "-------------------------------------------------------\n"
                    nineth_line = seventh_line
                    header_lines = [first_line, second_line, third_line, fourth_line, fifth_line, sixth_line, seventh_line]
    
                    # We want to ask the user what is the controlled bit of the transposed task data. In Dielectrics, this
                    # usually is the applied frequency or frequency.
    
                    for index, key in enumerate(main_task_keys_without_subtasks):
                        UserInput.post_status(str(index) + ": " + key)
    
                    question = {"question_title": "Attributes for file header",
                                "question_text": "Enter the numbers corresponding to the constants in the task. We are "
                                                 "working with transposed data, so this usually means that you want to "
                                                 "select frequency and maybe applied_frequency as keys. Those 2 should "
                                                 "suffice for the header. The numbers should only be separated by a comma.",
                                "default_answer": "0,3",
                                "optiontype": "multi_indeces"}
    
                    indeces_chosen = self._get_input(custom, question, template)
    
                    keys_for_file_header2 = []
                    for index in indeces_chosen:
                        keys_for_file_header2.append(main_task_keys_without_subtasks[index])
    
                    keys_for_file_header2.sort()
    
                    # Now we access each datarow we have
                    for main_task_data_point in main_task:
    
                        processing_log.append(time.strftime("%c") + ": Processing task {0}".format(str(number)))
    
                        # now we have a dictionary at hand of our datapoints and each datapoint of the main_task gets its
                        # own file
                        file_name = "{0}_Task{1}_{2}_{3}".format(self.name, str(number), file_number_str,
                                                                 str(main_task_data_point[key_for_file_name]))
    
                        # We need to count up the file number and ready the str of it
                        file_number += 1
                        file_number_str = "%05d" % (file_number,)  # we want leading 0s in the name so file explorers sort
                        # them correctly
    
                        outputfile = file_handler_2.create_file(file_name)
    
                        # Write the header
                        for line in header_lines:
                            outputfile.write_string(line)
    
                        # Write main task datapoint data (in this case modified for only needed keys
                        main_task_data_str = ""
                        for key in keys_for_file_header2:
                            main_task_data_str += "\t{0} {1}".format(str(key), str(main_task_data_point[key]))
    
                        outputfile.write_string(main_task_data_str)
    
                        outputfile.write_string(nineth_line)
    
                        # now gather every sub_task_datapoint (one line in the output file)
                        for sub_task_datapoint in main_task_data_point["sub_task_datapoints"]:
                            line_of_data = ""
                            # then iterate over every key so we can generate the one line
                            for key in keys_for_sub_task_datapoints:
                                line_of_data += "{0}\t".format(sub_task_datapoint[key])
                            outputfile.write_string(line_of_data)
    
                UserInput.post_status("Export is in progress. You should shortly see the files appearing.")
    
            # -------------------------------------------------------------------------------------------------------------
            # Step 9: Start File Output - this involves the output of the processing log as well as the task list and
            # closing all files
    
            UserInput.post_status("####################################")
            UserInput.post_status("-------------Making files-------------")
    
            processing_log.append(time.strftime("%c") + ": Entering step 9")
    
            print_following_steps(8)
            current_log_index = len(processing_log) - 1
    
            # We need to print out the processing log, the modified database itself and the task list.
            #TODO
            UserInput.post_status("Now Pickling the modified database. This could take some time!")
            processing_log.append(time.strftime("%c") + ": Starting pickling of processed database.")
            self.pickle_database("_processed")
            processing_log.append(time.strftime("%c") + ": Finished pickling.")
    
            processing_log.append(time.strftime("%c") + ": Starting file output for task list.")
            filehandler_for_task_list = FileHandler(self.pickle_path)
            task_list_file = filehandler_for_task_list.create_file("{0}_tasks".format(self.name))
    
            UserInput.post_status("Now reticulating splines. This could take some time.")
            for task in self.tasks:
                # Write all tasks into the buffer of the file
                task_list_file.write_string(str(task))
            # Now stop the file Handler
            filehandler_for_task_list.start()
            processing_log.append(time.strftime("%c") + ": Starting file output for first list.")
            # when we call start, we make a new Thread for the file handler which itself handles one file after the other
            file_handler_1.start()
            if user_wants_transposed:
                processing_log.append(time.strftime("%c") + ": Starting file output for second list.")
                file_handler_2.start()
    
            UserInput.post_status("Waiting on output1 to finish")
            file_handler_1.join()
    
            UserInput.post_status("Forgot some splines. Remedying that!")
            if user_wants_transposed:
                UserInput.post_status("Waiting on output2 to finish")
                # We can only wait on it if the user requested it and wants it
                file_handler_2.join()
    
            UserInput.post_status("Waiting on task_list_output to finish")
            filehandler_for_task_list.join()
            UserInput.post_status("Now saving processing log.")
            UserInput.post_status("I sincerely hope your time with JUMP was good!")
            filehandler_for_log = FileHandler(self.pickle_path)
            processing_log_file = filehandler_for_log.create_file("{0}_processing_log".format(self.name))
            for entry in processing_log:
                processing_log_file.write_string(str(entry))
            filehandler_for_log.start()
            filehandler_for_log.join()
            UserInput.post_status("Closed the log file. Bye bye!")
            
            
        
            
    def _get_input(self,custom,question,template=[]):
        #TODO
        """ 

        Parameters
        ----------
        custom : Boolean
            Decide wether to customize your measurement or use a template instead.
        question :
            Enter the posed question.
        template : 
            Enter a template, if custom=False.

        Returns chosen task.
        -------
        Private function in order to implement template data export. A list with all input parameters
        serves as template.
        
        """
        template=template;
        if custom:
            answer = UserInput.ask_user_for_input(question)["answer"]
            self.task_input.append(answer)
            return answer
        else:
            return template.pop(0)
        
    @property
    def tasks(self):
        return self.tasks_of_a_run

    @tasks.setter
    def tasks(self, task_list):
        self.tasks_of_a_run = task_list

    def add_point(self, identifier: [], Datapoint):
        # In this method should also probably go the logic to use the FileHandler to manage the file output for raw data
        # A datapoint looks like: {"R": 3, "X": 4}
        recursive_db = self.db
        for sub_part in identifier:
            recursive_db = recursive_db[sub_part]
        recursive_db["Datapoints"].append(Datapoint)

    def make_storage(self, identifier: [], data_source, human_readable_taskname: str):  # identifier:[0,1,3,2]
        data_level_dict = {"type": data_source, "Datapoints": [], "human_readable_task": human_readable_taskname}
        recursive_db_level = self.db
        level_depth = len(identifier) - 1
        # We start of at the top lebel db and then go deeper and deeper
        for index, temp_id in enumerate(identifier):
            # temp_id is a piece of the identifier.
            if temp_id not in recursive_db_level:
                if index == level_depth:
                    recursive_db_level[temp_id] = data_level_dict
                else:
                    recursive_db_level[temp_id] = {}
                    recursive_db_level = recursive_db_level[temp_id]
            else:
                recursive_db_level = recursive_db_level[temp_id]

    def calculate_all_values(self, geometry=None):
        """Traverses the database and calculates all calculatable values as implemented in DataManipulator

        :type geometry: dict
        :param geometry: dictionary containing thickness and area in mm as a float value respectively
        """
        for key in list(self.db.keys()):
            self._recursive_value_calc(self.db[key], geometry)

    def _recursive_value_calc(self, db_slice: dict, geometry=None):
        # first calculate all datapoints in the current depth
        for index, datapoint in enumerate(db_slice["Datapoints"]):
            db_slice["Datapoints"][index] = DataManipulator.calculate_non_geometry_dependent_values(datapoint)
            if geometry:
                db_slice["Datapoints"][index] = DataManipulator.calculate_geometry_dependent_values(
                    db_slice["Datapoints"][index], geometry)
        # then go deeper in all the other deeper lying subtasks
        for key in list(db_slice.keys()):
            if type(key) is int:
                self._recursive_value_calc(db_slice[key], geometry)

    def _get_datapoint_list_at_identifier(self, identifier):
        """returns the datapoint list with the specified identifier. If you manipulate this directly, you will directly
        manipulate the main_db as well

        :param identifier: a list in the usual identifier type
        :return: datapoints list at the specified identifier. Raises an IndexError if index isn't present
        """
        db_slice = self.db
        did_find_identifier = False
        # we need to match every component of the identifier
        for identifier_slice in identifier:
            did_find_identifier = False
            # then go over every key of the current db slice to see whether it matches
            for key in list(db_slice.keys()):
                # now check whether it matches
                if key == identifier_slice:
                    # if it matches, we go one level deeper with the respective key
                    db_slice = db_slice[key]
                    # and we did find the identifier_slice, so we can set that to true
                    did_find_identifier = True
                    break
        # if we finish thje for loop without having found the identifier, then it's not present in the database,
        # therefore we raise an error
        if not did_find_identifier:
            raise IndexError("Didn't find the identifier in the database")

        return db_slice["Datapoints"]

    def _merge_two_datapoint_lists(self, datapointlist1, datapointlist2):

        """Takes two lists that are directly in the database and updates the first list with the content of the
        second one in place

        :param datapointlist1:
        :param datapointlist2:
        :return:
        """

        # we update the first item of datapoints1 with the first item of datapoints2. This 1 by 1 of both lists is
        # achieved by "zip", which makes sure that we're always at the same index in both lists
        for point1, point2 in zip(datapointlist1, datapointlist2):  # type: dict
            # in case data with the exact same key is already present, it gets overwritten as expected and documented
            point1.update(point2)
        return

    def merge_same_level_datapoints(self, identifier1, identifier2):

        """Takes two identifiers of two equal levelled adjacent datarows and merges them into the first identifiers
        datarow

        :param identifier1: identifier as a list of the first datarow
        :param identifier2: identifier as a list of the second datarow that's gonna be merged into the first one's
        """
        # we get direct lists of both datapoint rows
        datapoints1 = self._get_datapoint_list_at_identifier(identifier1)  # type: dict
        datapoints2 = self._get_datapoint_list_at_identifier(identifier2)  # type: dict

        shortened_id1 = identifier1[:-1]
        shortened_id2 = identifier2[:-1]
        if shortened_id1 != shortened_id2:
            raise LevelError("Your two levels don't have the same base identifier! What you want to do doesn't "
                             "make sense!")

        self._merge_two_datapoint_lists(datapoints1, datapoints2)
        return

    def merge_diff_level_datapoints(self, identifier1, identifier2):
        """Merges into first identifier. Make sure that the first identifier is the one with the higher level
        (outermost)

        :param identifier1:
        :param identifier2:
        """
        datapoints1 = self._get_datapoint_list_at_identifier(identifier1)  # type: dict
        datapoints2 = self._get_datapoint_list_at_identifier(identifier2)  # type: dict

        shortened_id1 = identifier1
        shortened_id2 = identifier2[:-1]

        if shortened_id1 != shortened_id2:
            raise LevelError("You tried to merge two datapoints accross multiple levels, merge sequentially instead "
                             "inner-most outwards")

        self._merge_two_datapoint_lists(datapoints1, datapoints2)

        return

    def _attach_sub_datapoints_into_parent_datapoint(self, parent_data_points: list, sub_task_datapoints: list):
        parent_len = len(parent_data_points)
        sub_len = len(sub_task_datapoints)

        number_of_sub_points_per_parent, remainder = divmod(sub_len, parent_len)

        if remainder > 0:
            # the last item obviously isn't finished of sorts, but we may still want to insert all other points
            parent_len -= 1

        for index, parent_datapoint in enumerate(parent_data_points):
            # this if condition is true in case we shortened the parent_len. This means the last point isn't yet ready
            # to be calculated. But after measurement, this should always be false and therefore go into the code block
            if not index == parent_len:

                # only create the sub_task_datapoints entry in the dict if it's not already present. If it's present,
                # we don't touch it. this makes it possible to run this method repeatedly without blowing up the list.
                # If one wants to merge multiple sub_tasks into the parent, one should first merge the two sub_tasks
                # with the merge_same_level_datapoints method.
                if "sub_task_datapoints" not in parent_datapoint:
                    parent_datapoint["sub_task_datapoints"] = []

                    # we must include n-elements into the parent whereby n is the number of sub points per parent
                    for n_th_sub_index in range(number_of_sub_points_per_parent):
                        index_in_sub_task_list = index * number_of_sub_points_per_parent + n_th_sub_index
                        parent_datapoint["sub_task_datapoints"].append(sub_task_datapoints[index_in_sub_task_list])

    def insert_sub_datapoints_into_parent_datapoint(self, parent_identifier, sub_identifier):

        parent_datapoints = self._get_datapoint_list_at_identifier(parent_identifier)
        sub_task_datapoints = self._get_datapoint_list_at_identifier(sub_identifier)

        self._attach_sub_datapoints_into_parent_datapoint(parent_datapoints, sub_task_datapoints)

    def get_transposed_parent_child_datapoints(self, identifier):
        """What we want is the child's data as well as the child's main identifier as new parent and the previous parent
        as child. In a concrete example, our old parent is a setpoint and a measured temperature list. as sub_tasks,
        there are then for every temperature the same 3 frequencies but of course not with the same result (temperature
        dependence...). This means we want the datapoints (frequency reponse) in the new child as well. But we want to
        map it in a different way.So the result is a list that contains only datapoints with ["sub_task_datapoints"].

        :return: the transposed datapoints
        :rtype: list
        :param identifier: the identifier of the parent
        """
        switched_datapoints = []
        datapoints = self._get_datapoint_list_at_identifier(identifier)

        # create top level, measured values will be bullshit but also, it will only ever plot 1 value (eg freq) from
        # top level
        for sub_item in datapoints[0]["sub_task_datapoints"]:
            switched_datapoints.append(sub_item)

        # we need to deep copy otherwise the sub_dicts and lists will be altered in the original, too
        raw_parent_list = copy.deepcopy(datapoints)

        # then we dont' want any sub_tasks here because these will be the new childs and the whole purpose of
        # transposing is getting rid of sub_tasks at this level
        for point in raw_parent_list:
            del point["sub_task_datapoints"]

        # now here we use our freshly created "switched datapoints" list and then go through each of them, adding
        # in both the previous parents as well as the datapoints
        for index_of_new_parent, new_parent in enumerate(switched_datapoints):
            # this is the list of sub_tasks for the new parent we are manipulating right now
            list_for_sub_merging_with_raw_parents = []
            # we go through each of the old_parent and pick the index_of_new_parent-th element in the subtasks
            for item in datapoints:
                list_for_sub_merging_with_raw_parents.append(item["sub_task_datapoints"][index_of_new_parent])
            # we then merge it so we have in the example the actual datapoint now merged with the temperature
            self._merge_two_datapoint_lists(list_for_sub_merging_with_raw_parents, raw_parent_list)
            # and finally add the newly created sub_task_list for the new parent into it - we are still in the loop
            # iterating over every new_parent
            new_parent["sub_task_datapoints"] = list_for_sub_merging_with_raw_parents

        return switched_datapoints


class DataManipulator:
    epsilon0 = 8.85418782e-15  # use geometry in mm!!!!!!!

    @staticmethod
    def calculate_non_geometry_dependent_values(datapoint: dict):
        """

        :param datapoint:
        :return: new_datapoint with all values
        """
        datapoint_to_mangle = datapoint.copy()
        did_calculate_something = True

        while did_calculate_something:
            did_calculate_something = False
            existing_keys = list(datapoint_to_mangle.keys())  # type: list

            # first check whether we have to go through existing sub_task_datapoints, if there are, calculate them
            # accordingly, could probably move out of the while loop but let's see how it goes
            if "sub_task_datapoints" in existing_keys:
                for sub_index, sub_point in enumerate(datapoint["sub_task_datapoints"]):
                    datapoint["sub_task_datapoints"][
                        sub_index] = DataManipulator.calculate_non_geometry_dependent_values(sub_point)

            # to save performance, we first check whether the result exists, we could also change to a scheme of putting
            #  a key "did_calculate_B" in the dict if these comparisons are too slow
            if "Z_comp" not in existing_keys:
                # Code to calculate Z_complex

                # and then check the 2 things (or more) we need to calculate it, whether they are available
                if "R" in existing_keys and "X" in existing_keys:
                    z_comp = complex(datapoint_to_mangle["R"], datapoint_to_mangle["X"])
                    z_real = z_comp.real
                    z_imag = z_comp.imag
                    datapoint_to_mangle["Z_comp"] = z_comp
                    existing_keys.append("Z_comp")
                    datapoint_to_mangle["Z_real"] = z_real
                    existing_keys.append("Z_real")
                    datapoint_to_mangle["Z_imag"] = z_imag
                    existing_keys.append("Z_imag")
                    did_calculate_something = True

            if "Y_comp" not in existing_keys:

                if "Z_comp" in existing_keys:
                    y_comp = 1 / datapoint_to_mangle["Z_comp"]
                    y_real = y_comp.real
                    y_imag = y_comp.imag
                    datapoint_to_mangle["Y_comp"] = y_comp
                    existing_keys.append("Y_comp")
                    datapoint_to_mangle["Y_real"] = y_real
                    existing_keys.append("Y_real")
                    datapoint_to_mangle["Y_imag"] = y_imag
                    existing_keys.append("Y_imag")
                    did_calculate_something = True

            if "G_one_prime" not in existing_keys:

                if "Y_real" in existing_keys:
                    g_one_prime = datapoint_to_mangle["Y_real"]
                    datapoint_to_mangle["G_one_prime"] = g_one_prime
                    existing_keys.append("G_one_prime")
                    did_calculate_something = True

            if "G_two_prime" not in existing_keys:

                if "Y_imag" in existing_keys:
                    g_two_prime = datapoint_to_mangle["Y_imag"]
                    datapoint_to_mangle["G_two_prime"] = g_two_prime
                    existing_keys.append("G_two_prime")
                    did_calculate_something = True

            if "B" not in existing_keys:

                if "G_two_prime" in existing_keys:
                    b = datapoint_to_mangle["G_two_prime"]
                    datapoint_to_mangle["B"] = b
                    existing_keys.append("B")
                    did_calculate_something = True

            if "Omega" not in existing_keys:

                if "freq" in existing_keys:
                    omega = datapoint_to_mangle["freq"] * 2 * cmath.pi
                    datapoint_to_mangle["Omega"] = omega
                    existing_keys.append("Omega")
                    did_calculate_something = True

            if "C_prime" not in existing_keys:

                if "G_two_prime" in existing_keys and "Omega" in existing_keys:
                    c_prime = datapoint_to_mangle["G_two_prime"] / datapoint_to_mangle["Omega"]
                    datapoint_to_mangle["C_prime"] = c_prime
                    existing_keys.append("C_prime")
                    did_calculate_something = True

            if "Phase" not in existing_keys:

                if "G_one_prime" in existing_keys and "G_two_prime" in existing_keys:
                    phase = cmath.phase(complex(datapoint_to_mangle["G_one_prime"], datapoint_to_mangle["G_two_prime"]))
                    datapoint_to_mangle["Phase"] = phase
                    existing_keys.append("Phase")
                    did_calculate_something = True

                elif "G_one_prime" in existing_keys and "B" in existing_keys:
                    phase = cmath.phase(complex(datapoint_to_mangle["G_one_prime"], datapoint_to_mangle["B"]))
                    datapoint_to_mangle["Phase"] = phase
                    existing_keys.append("Phase")
                    did_calculate_something = True

                elif "G_one_prime" in existing_keys and "C_prime" in existing_keys and "Omega" in existing_keys:
                    phase = cmath.phase(complex(datapoint_to_mangle["G_one_prime"], (datapoint_to_mangle["C_prime"] *
                                                                                     datapoint_to_mangle["omega"])))
                    datapoint_to_mangle["Phase"] = phase
                    existing_keys.append("Phase")
                    did_calculate_something = True

            if "log_freq" not in existing_keys:

                if "freq" in existing_keys:
                    log_freq = math.log10(datapoint_to_mangle["freq"])
                    datapoint_to_mangle["log_freq"] = log_freq
                    did_calculate_something = True

        return datapoint_to_mangle

    @staticmethod
    def calculate_geometry_dependent_values(datapoint, geometry):
        """

        :param datapoint: a dictionary of the datapoint itself
        :param geometry: dictionary containing the keys "thickness" and "area" in mm, eg {"thickness": 3, "area": 7}
        :return:
        """
        datapoint_to_mangle = datapoint.copy()
        thickness = geometry["thickness"]
        area = geometry["area"]
        did_calculate_something = True

        while did_calculate_something:
            did_calculate_something = False
            existing_keys = list(datapoint_to_mangle.keys())  # type: list

            # first check whether we have to go through existing sub_task_datapoints, if there are, calculate them
            # accordingly, could probably move out of the while loop but let's see how it goes
            if "sub_task_datapoints" in existing_keys:
                for sub_index, sub_point in enumerate(datapoint["sub_task_datapoints"]):
                    datapoint["sub_task_datapoints"][
                        sub_index] = DataManipulator.calculate_geometry_dependent_values(sub_point, geometry)

            if "Epsilon_one_prime" not in existing_keys:

                if "C_prime" in existing_keys:
                    numerator = datapoint_to_mangle["C_prime"] * thickness
                    denominator = DataManipulator.epsilon0 * area
                    epsilon_one_prime = numerator / denominator
                    existing_keys.append("Epsilon_one_prime")
                    datapoint_to_mangle["Epsilon_one_prime"] = epsilon_one_prime
                    did_calculate_something = True

            if "Epsilon_two_prime" not in existing_keys:

                if "G_one_prime" in existing_keys and "Omega" in existing_keys:
                    numerator = datapoint_to_mangle["G_one_prime"] * thickness
                    denominator = DataManipulator.epsilon0 * datapoint_to_mangle["Omega"] * area
                    epsilon_two_prime = numerator / denominator
                    existing_keys.append("Epsilon_two_prime")
                    datapoint_to_mangle["Epsilon_two_prime"] = epsilon_two_prime
                    did_calculate_something = True

            if "Tan_delta" not in existing_keys:

                if "Epsilon_one_prime" in existing_keys and "Epsilon_two_prime" in existing_keys:
                    tan_delta = datapoint_to_mangle["Epsilon_two_prime"] / datapoint_to_mangle["Epsilon_one_prime"]
                    existing_keys.append("Tan_delta")
                    datapoint_to_mangle["Tan_delta"] = tan_delta
                    did_calculate_something = True

            if "Sigma_comp" not in existing_keys:

                if "Y_comp" in existing_keys:
                    # Sigma wird in 1/Ohm*cm angegeben. Wenn wir Dicke/Z*Fläche alles in mm haben, haben wir mm/mm^2
                    # sprich 1cm/10 *`100/1cm^2, im Endeffekt daher *10
                    sigma_comp = thickness * 10 / (area * datapoint_to_mangle["Z_comp"])
                    existing_keys.append("Sigma_comp")
                    datapoint_to_mangle["Sigma_comp"] = sigma_comp
                    sigma_one_prime = sigma_comp.real
                    existing_keys.append("Sigma_one_prime")
                    datapoint_to_mangle["Sigma_one_prime"] = sigma_one_prime
                    sigma_two_prime = sigma_comp.imag
                    existing_keys.append("Sigma_two_prime")
                    datapoint_to_mangle["Sigma_two_prime"] = sigma_two_prime
                    did_calculate_something = True

            if did_calculate_something:
                # just add thickness and area to the datapoits as well to know what was used to calculate the values
                datapoint_to_mangle["Thickness"] = thickness
                datapoint_to_mangle["Area"] = area

        return datapoint_to_mangle


class LevelError(Exception):
    """class to indicate something in the database levels was wrong

    """

    def __init__(self, mismatch):
        Exception.__init__(self, mismatch)


        # with open('database_test.pkl', 'wb') as output:
        #  pickle.dump(main_db, output, -1)


class FileHandler(Thread):
    """Create files fast, threaded and write data into them. There are two way to use this. You can use it to batch
    process created files or to give you an OutPutfile that you can continuesly put stuff to it and later mark it
    for final output. When you made sure that you wrote all the data for a file in its buffer (write_data method of the
    output file pointer), then start the output by calling start() on the filehandler object for that file(s). When you
    later want to make sure that all files have finished processing, just call the join() method on the fileHandler
    object. You can see how it can be done in the _post_process method at the very bottom.

    """

    def __init__(self, directory_base=""):
        super().__init__()
        self.list_of_files = []  # type: [OutputFile]
        self.directory_base = directory_base
        self.did_finish_starting_asynchronous = False
        if not os.path.isdir(directory_base):
            os.makedirs(directory_base)

    def create_file(self, name):
        """Creates file and if necessary the containing folder for the file. Appends .txt automatically

        :param name:
        :rtype: OutputFile
        """
        path_and_name = self.directory_base + name + ".txt"
        output_file = OutputFile(path_and_name)
        self.list_of_files.append(output_file)
        return output_file

    def write_once_one_threaded(self):
        for file in self.list_of_files:     # type:OutputFile
            file.start()
            file.should_start_writing = True
            file.should_finish = True
            file.join()
        self.did_finish_starting_asynchronous = True

    def _close_everything(self):  # Make sure to call the Threads' join method once at the end
        for file in self.list_of_files:     # type:OutputFile
            file.should_finish = True

        while not self.did_finish_starting_asynchronous:
            time.sleep(0.1)
        for file in self.list_of_files:     # type:OutputFile
            file.join()

    def get_files(self):
        return self.list_of_files

    def run(self):
        self.write_once_one_threaded()

    def join(self, timeout=None):
        self._close_everything()
        super().join()


class OutputFile(Thread):
    """
        my class to manage writing to a file by polling a queue at least every 0.5 seconds, but in fact faster
    """

    def __init__(self, path_and_name: str):
        super().__init__()
        self.should_start_writing = False
        self.has_started_writing = False
        self.should_finish = False
        self.path_and_name = path_and_name  # type: str
        self.queue = queue.Queue()

    def run(self):
        self._write_data()

    def write_string(self, newline_to_add: str):
        self.queue.put(newline_to_add)

    def _write_data(self):
        # At the risk of crashing when a file can't be opened, we gain the perceived speedyness because we only open
        # files for writing when the user is not directly interacting anymore
        while not self.should_start_writing:
            time.sleep(0.1)

        # Now open the file
        self.file = open(self.path_and_name, 'a')

        while not self.should_finish or not self.has_started_writing:
            # When we entered this not self.should_finish loop, we made sure that we started writing. As a result,
            # we can safely set has_started_writing to True
            self.has_started_writing = True
            # Now check whether queue is empty or not
            while not self.queue.empty():
                # write the string in the queue to the file
                self.file.write(self.queue.get() + "\n")
                # notify the queue that the task is done
                self.queue.task_done()
                # if nothing is in the queue, wait for 0.5 seconds
                if self.queue.empty():
                    time.sleep(0.1)
        self.file.close()


main_db = Database()
