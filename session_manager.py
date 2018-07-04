from flask import Blueprint, Flask, url_for
from flask import jsonify
import requests
from flask import request
import json
import sys, traceback
from copy import deepcopy

rasa_IP = "100.88.8.41:5000"
SessionMGR = Blueprint('SessionMGR',__name__)
INTENT_REPEAT = 'repeat'
INTENT_LIST_VM = 'list_VM'
INTENT_SHOW_USAGE = 'show_usage'
INTENT_RESTART_VM = 'restart_VM'
ITENT_NONE = 'None'

@SessionMGR.route('/test2', methods=['POST'])
# Testing the state session thingy
def api_test2():
    print("testing Connectivity")
    try:
        # This section pertains to conveying the user query to the NLP reply and retrieving the NLP module's reply
        # Receive the message from the frontEnd
        request_json = request.get_json(force=True)# You'll get a dictionary
        print(type(request_json))
        #request_json = json.dumps(request_json)
        print("Request received: {}".format(request_json))
        rasa_IP ="100.88.8.41:5000"
        print("DataType sent to NLP server: {}".format(type(request_json)))
        nlp_message = requests.post(url='http://{}/parse'.format(rasa_IP), data=json.dumps(request_json))
        nlp_reply = nlp_message.json() # Check the JSON Response Content documentation below
        print("NLP reply: {}".format(nlp_reply))
        #response_json = processNLP(nlp_Reply)
        nlp_reply['q'] = request_json['q']
        query = Query(nlp_reply)

        #TODO: return a JSON key containing the intent
        #TODO: data
        #TODO: If user is to list backend; send server names (array of strings)
        session_response = {}
        session_response["NLPintent"] = query.get_intent()
        session_response["data"] = sessionMGR.receive_query(query)
        return jsonify(session_response)
    except Exception as ex:
        _, _, exc_traceback = sys.exc_info()
        session_response = {}
        session_response["message"] =  "error in processing sent request: {}".format(str(ex))
        session_response["data"] = []
        session_response["intent"] = "None"
        print(str(ex))
        print(traceback.print_tb(exc_traceback, file=sys.stdout))
        return jsonify(session_response)

def setup():
        return [SessionMGR]



#Assume JSON is prepared before creating a query instance
class Query:
    def __init__(self, json_data):
        self.identifier = "a"
        self.json = json_data
        self.intent = self.json["intent"]["name"]
        self.entities = {}
        self.query = json_data['q']
        entity_list = self.json["entities"]
        for entity in entity_list:
            entity_type =entity["entity"]
            start_index = entity['start']
            end_index = entity['end']
            self.entities[entity_type] = self.json["text"][start_index:end_index]
        print("Entities captured: {}".format(self.entities))

    def get_identifier(self):
        return self.identifier

    def get_intent(self):
        return self.intent

    def get_entities(self):
        return self.entities

class Session:
    def __init__(self, identity, args=None, fn=None):
        self.identifier = identity
        #self.cu
        self.completion_status = False
        self.chat_history = []
        self.arg_dict = args
        self.function = fn

        # For context awareness
        self.last_query = None

        # for slot filling
        self.incompleted = False

    def handle_updated_query(self, query_object):
        self.arg_dict[self.filling_param] = query_object.query
        query_object.intent = self.last_query.get_intent()


    def process_query(self, query_object):

        if self.incompleted:
            self.handle_updated_query(query_object)
        else:
            entity_args = query_object.get_entities()

            print("Entities captured: {}, checking the dictionary keys now \n".format(entity_args))
            for entity_type in entity_args.keys():
                print("Checking for {} in {}\n".format(entity_type, entity_args.keys()))
                entity_value = entity_args[entity_type]
                if (entity_type in self.arg_dict.keys() and self.arg_dict.get(entity_type,0)!= 0):
                    self.arg_dict[entity_type] = entity_value

        #After filling the argument slots, check if all required arguments are flled
        if(None in self.arg_dict.values()):
            # slot filling
            self.incompleted = True
            print("Missing values detected!")
            missing_parameters = [i for i in self.arg_dict.keys() if self.arg_dict[i] is None]

            self.filling_param = missing_parameters[0]
            reply = "Could you specify the "+self.filling_param+"?"

            return reply
        #All arguments filled; proceed to call the function
        else:
            self.incompleted = False
            print("All required arguments filled, calling function now")
            if(bool(self.arg_dict)):
                reply = self.function(**self.arg_dict)
            else:
                reply = self.function()
            return reply
        #TODO: completion status
        #TODO: deal with the issue of argparsing
        #TODO: return the response
        #TODO: implement cancellation of session


    def get_completion_status(self):
        return self.completion_status
    def get_entities(self):
        return self.entities

    #TODO: Implement terminate session
    def terminate_session(self):
        return "terminate session"

    def update(self, fn, arg_dict):
        print("Updating function {} to {}".format(self.function, fn))
        self.arg_dict = deepcopy(arg_dict)
        self.function = fn

    def process_context(self, query_object):
        # Return:
        #   None: not applicable for context awareness
        #   0: no entities can be identified or entity doesn't match
        #   query_object: context awared query_object
        intent = query_object.get_intent()
        if intent != INTENT_REPEAT or self.last_query is None:
            return None
        else:
            entities = query_object.get_entities()
            if len(entities) == 0:
                return 0 # no entities can be identified
            else:
                try:
                    new_query = self.last_query
                    for key in entities.keys():
                        new_query.entities[key] = entities[key]
                    return new_query
                except:
                    return 0
class Session_Manager:
    def __init__(self, args_required, intent_functions):
        self.sessions = {}
        self.args_required = args_required
        self.intent_functions = intent_functions

    def get_sessions(self):
        return self.sessions

    def create_session(self,identity, query):
        # Intent
        # Identifier
        identifier = identity
        answer = None
        new_session = Session(identifier)
        new_session.last_query = query
        self.sessions[identifier] = new_session
    def receive_query(self,query):
        identifier = query.get_identifier()

        #If query identifier not in dictionary, create a new session, else process the query
        if identifier not in self.sessions:
            self.create_session(identifier, query)
        session = self.sessions[identifier]

        if not session.incompleted: # check if need slot filling

            # for context awareness
            context_query = session.process_context(query)
            if context_query == 0:
                # A context query but entities not match, return not understandable
                return "Sorry, I am not sure I understand"
            elif context_query is not None:
                # A context query
                query = context_query
            else: # not a context query
                session.last_query = query
            # context awareness ends

            # Update the fn and the arg_dict
            query_intent = query.get_intent()
            if query_intent in self.args_required.keys() and query_intent != "None" or query_intent != "repeat":
                arg_dict = self.args_required[query_intent]
                fn = self.intent_functions[query_intent]
                session.update(fn, arg_dict)
        answer = session.process_query(query)
        # Session response handling
        session_response = {}
        session_response["status"] = "completed" if not session.incompleted else "incompleted"
        session_response['message'] = answer
        session_response["intent"] = query.get_intent()
        session_response["missing_arg"] = session.filling_param if session.incompleted else "None"
        session_response["data"] = []

        if session.incompleted:
            if session.filling_param == "VM":
                session_response["data"] = list_VM()
        elif(query.get_intent() in self.args_required.keys()):
            session_response["data"] = answer

        # Check for completion
        # TODO: keep server in memory
        completion_status = session.get_completion_status()
        if(completion_status):
            self.remove_session(identifier)
        return session_response
    def remove_session(self,identifier):
        # get Session to send termination message?
        del self.sessions[identifier]


def show_usage(resource=None,VM=None,duration=None):
    if resource is None or VM is None or duration is None:
        raise Exception("arguments not fully provided")
    reply = "showing resource {}".format(resource)
    print(reply)
    return [['June 1',0.2],['June 2',0.4],['June 3',0.05],['June 4',0.15],['June 5',0.8]]

def list_VM():
    print("Listing VMS")
    backend_IP = "202.183.76.61"
    reply = requests.get(url='http://{}/listallvms'.format(backend_IP)).json()
    print("Reply :", reply)
    return reply["response"]

def restart_VM(VM=None):
    if VM is None:
        raise Exception("VM is not provided")
    server = VM
    print("Restarting {}".format(server))
    reply = requests.get(url='http://202.183.76.61/rebootserver/{}'.format(server))
    reply = reply.text
    print("Reply: {}".format(reply))
    return reply

def help():
    return "Hi, I can help you with \n1.list your VMs\nshow VM resource usage\nrestart Vms"

def welcome():
    return "Hello, how can I help you:)"

args_required = {"show_usage":{"resource":None, "VM":None, "duration":None}, "list_VM":{}, "restart_VM":{"VM": None},
        "help":{}, "welcome":{}}
intent_function = {"show_usage": show_usage, "list_VM": list_VM, "restart_VM": restart_VM, "help":help, "welcome":welcome}
sessionMGR = Session_Manager(args_required, intent_function)
