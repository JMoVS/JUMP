__author__ = 'Justin Scholz'
__copyright__ = "Copyright 2015 - 2017, Justin Scholz"

def recognize_user_input_yes_or_no(user_choice: str, default: bool):
    user_input_understood = False
    yes = str
    no = str
    user_choice_answer = "x"
    if default:
        yes = ""
        no = "no"
    elif not default:
        yes = "yes"
        no = ""
    if user_choice == yes or user_choice == "y" or user_choice == "yes":
        user_choice_answer = True
        user_input_understood = True
    elif user_choice == no or user_choice == "n" or user_choice == "no":
        user_choice_answer = False
        user_input_understood = True
    return user_choice_answer, user_input_understood


def recognize_user_input_multi_choice(user_choice: str, user_options):
    user_input_understood = False
    user_choice_answer = int
    for answer_index in range(user_options):
        try:
            if int(user_choice) == answer_index:
                user_choice_answer = answer_index
                user_input_understood = True
        except ValueError:
            user_input_understood = False
    return user_choice_answer, user_input_understood


def parse_user_input_lower_upper_limit_with_interval(user_choice: float, lower_limit: float, upper_limit: float,
                                                     steplength: float):
    user_input_understood = False
    # First we check that the entered value is in the expected boundaries
    if not (user_choice > upper_limit or user_choice < lower_limit):
        # then we use mathematics to look whether it matches with our desired step length
        reduced = ((user_choice - lower_limit) * steplength)
        reduced = round(reduced, 4)
        # And do stupid things because computers calculate in base 2 and not base 10
        if reduced.is_integer():
            user_input_understood = True
    return user_choice, user_input_understood


def recognize_user_input(user_choice: str, possibilities: [], default_answer=None):
    """

    :param default_answer: the default answer that is returned if user just hits enter
    :param user_choice: what the user entered
    :param possibilities: a list containing all valid answers, make sure to include "" if you want default answers
    with "enter" key pressing
    :return: user_chosen_answer: one value of the possibilities passed to this function; user_input_understood: Whether
     there was an error parsing the answer or not. Returns true if the input was matched.
    """
    user_input_understood = False
    user_chosen_answer = str
    for answer in possibilities:
        try:
            if int(user_choice) == answer:
                user_chosen_answer = user_choice
                user_input_understood = True
        except ValueError:
            user_input_understood = False
    if user_choice == "":
        user_chosen_answer = default_answer
        user_input_understood = True
    return user_chosen_answer, user_input_understood


def ask_user_for_input(question: dict):
    """

    :param question: a dictionary as it comes from elsewhere, meaning that it has the keys: "question_title", "question_text",
    "default_answer",  "option_type" (can be "yes_no", "multi_choice", "free_choice"),
    "valid_options" (only needed for multi_choice), "valid_options_lower_limit" and "valid_options_upper_limit" and
    "valid_options_steplength" in case of the free_choice. The "default answer" key is in case of a yes/no question
    either True or False, in case of free choice, it's a float and in case of multi_choice, it's the index of the answer
    out of the valid_options.
    :type question: dict
    - a sample dictionary for multi_choice is:
    question = {"question_title": "Measurement Mode",
                    "question_text": "Please choose which measurement mode to use",
                    "default_answer": 2,
                    "optiontype": "multi_choice",
                    "valid_options": ["2-point", "3-point", "4-point"]}
    - a sample dictionary for yes/no is:
    question = {"question_title": "Connection check",
                        "question_text": "Connection check wasn't performed but is optional. Do you want to check the "
                                         "connections?",
                        "default_answer": True,
                        "optiontype": "yes_no"}
    - a sample dictionary for interval is:
    question = {"question_title": "Excitation voltage",
                    "question_text": "Please enter an excitation voltage between 0 and 3 V. Maximum accuracy is 0.1 V.",
                    "default_answer": 1.0,
                    "optiontype": "free_choice",
                    "valid_options_lower_limit": 0.0,
                    "valid_options_upper_limit": 3.0,
                    "valid_options_steplength": 1e1}
            Note: Steplength is the inverse steplength. If 0.05 is the allowed steplength, enter 20 as steplength here
    - a sample dictionary to ask for free text:
    question = {"question_title": "Working directory",
                "question_text": "Please choose a working directory for the following session with this program",
                "default_answer": "C:\Data\DiBaMePro",
                "optiontype": "free_text"}
    - a sample dictionary to ask for two indeces:
    question = {"question_title": "Same-level-merge selection",
                            "question_text": "Please enter the two indeces, (you will get two input prompts) for the "
                                             "two which are to be merged.",
                            "default_answer": "0",
                            "optiontype": "2_indeces"}
    - a sample dictionary to ask for multiple indeces:
    question = {"question_title": "Same-level-merge selection",
                            "question_text": "Please enter one or more indeces separated only by a comma",
                            "default_answer": "0,4,8,12",
                            "optiontype": "multi_indeces"}
    """
    result = question.copy()

    # first we get the dictionarie's values into local variables to ease the handling
    question_title = question["question_title"]  # type: str
    question_title = "-------------" + question_title + "-------------"
    question_text = question["question_text"]  # type: str
    default_answer = question["default_answer"]  # can be int or True or str
    optiontype = question["optiontype"]  # type: str
    valid_options = None
    valid_options_lower_limit = None
    valid_options_upper_limit = None
    valid_options_steplength = None

    print(question_title)
    print(question_text)

    # valid_options and option specifics only exist if it's not a yes/no question
    if optiontype != "yes_no":
        # in case of multi_choice, key "valid_options" exist and we need to match it
        if optiontype == "multi_choice":
            valid_options = question["valid_options"]  # type: []
        elif optiontype == "free_choice":
            valid_options_lower_limit = question["valid_options_lower_limit"]
            valid_options_upper_limit = question["valid_options_upper_limit"]
            valid_options_steplength = question["valid_options_steplength"]

    # Now let's make different parsing for the (currently) three question types:
    # Yes/No questions are mapped to Bool True or False
    if optiontype == "yes_no":
        # here we can easily centrally exchange this to some logic to talk to a potential GUI
        answer_understood = False
        user_chosen_answer = None  # type: bool
        default_literal_answer = ""
        if default_answer:
            default_literal_answer = "yes"
        elif not default_answer:
            default_literal_answer = "no"
        while not answer_understood:
            user_entered_response = input(
                "Default answer is: " + default_literal_answer + ". What do you want? Type y, n or confirm default: ")
            user_chosen_answer, answer_understood = recognize_user_input_yes_or_no(user_entered_response,
                                                                                   default_answer)
        result['answer'] = user_chosen_answer

    # Code Block for handling multi-option question type
    elif optiontype == "multi_choice":
        # we will later need a list of valid responses from the user
        valid_answers = []
        # enumerate yields the index AND the value, so we can use both then
        for index, item in enumerate(valid_options):
            print(str(index) + ": " + item)
            valid_answers.append(index)
        answer_understood = False
        user_chosen_answer = None  # type: str
        while not answer_understood:
            print("The default is option #" + str(default_answer))
            user_entered_response = input("Confirm with enter or put in your own choice and confirm: ")
            user_chosen_answer, answer_understood = recognize_user_input(user_entered_response, valid_answers,
                                                                         default_answer)
        result['answer'] = int(user_chosen_answer)

    elif optiontype == "free_choice":
        answer_understood = False
        user_chosen_answer = None
        while not answer_understood:
            print("Default answer is: " + str(default_answer))
            user_entered_response = input("Please enter your desired value with '.' as decimal separator: ")
            try:
                user_entered_response = float(user_entered_response)
                user_chosen_answer, answer_understood = parse_user_input_lower_upper_limit_with_interval(
                    user_entered_response, valid_options_lower_limit, valid_options_upper_limit,
                    valid_options_steplength)
            except ValueError:
                try:
                    if user_entered_response == "":
                        user_chosen_answer = default_answer
                        answer_understood = True
                except ValueError:
                    answer_understood = False
        result['answer'] = user_chosen_answer

    elif optiontype == "free_text":
        answer_understood = False
        user_chosen_answer = None
        while not answer_understood:
            print("Default answer is: " + str(default_answer))
            user_chosen_answer = input("Type your own now or confirm default with enter: ")
            if user_chosen_answer == "":
                user_chosen_answer = default_answer
            answer_understood = True
        result['answer'] = user_chosen_answer

    elif optiontype == "2_indeces":
        answer1_understood = False
        answer2_understood = False
        index1 = None
        index2 = None
        print("Default answer is: " + str(default_answer))
        while not answer1_understood:
            user_chosen_answer = input("Index 1: ")
            try:
                index1 = int(user_chosen_answer)
                answer1_understood = True
            except ValueError:
                print("Please make sure to only enter a number!")

        while not answer2_understood:
            user_chosen_answer = input("Index 2: ")
            try:
                index2 = int(user_chosen_answer)
                answer2_understood = True
            except ValueError:
                print("Please make sure to only enter a number!")

        result["answer"] = [index1, index2]

    elif optiontype == "multi_indeces":
        answer_understood = False
        user_chosen_answer = default_answer
        indeces = None
        while not answer_understood:
            indeces = []
            print("Default answer is: " + str(default_answer))
            user_chosen_answer = input("Type your own now or confirm default with enter: ") # type: str
            user_chosen_answer_list = user_chosen_answer.split(",")
            error_happened = False
            for item in user_chosen_answer_list:
                try:
                    indeces.append(int(item))
                except ValueError:
                    error_happened = True
                    print("Please make sure to only enter integer numbers separated by commas.")
            if not error_happened:
                answer_understood = True
        result["answer"] = indeces


    else:
        print("You are trying to use a question type that is not supported or have a typoo in your code.+")

    return result  # type: dict


def confirm_warning(warning_text: str):
    # GUI code to make a window that just has an OK button
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print(warning_text)
    print("")
    print("Confirm with Enter!")
    input("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")


def post_status(new_status: str):
    # GUI code to show log messages that don't need confirmation!
    print(str(new_status))
