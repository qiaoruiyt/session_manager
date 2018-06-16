# -*- coding: utf-8 -*-
"""
Created on Fri Jun  1 10:02:40 2018
This is the python file containing the Session Manager
@author: Sidney
"""
from flask import Blueprint, Flask, url_for
from flask import jsonify
import requests
from flask import request
import json

nlp_docker_IP = "192.168.99.100:5000"
SessionMGR = Blueprint('SessionMGR',__name__)

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
        rasa_IP ='192.168.99.100:5000'
        print("DataType sent to NLP server: {}".format(type(request_json)))
        nlp_message = requests.post(url='http://{}/parse'.format(rasa_IP), data=json.dumps(request_json))
        nlp_reply = nlp_message.json() # Check the JSON Response Content documentation below
        print("NLP reply: {}".format(nlp_reply))
        #response_json = processNLP(nlp_Reply)
        response_json = nlp_reply
        query = Query(nlp_reply)
        
        #TODO: return a JSON key containing the intent
        #TODO: data 
        #TODO: If user is to list backend; send server names (array of strings)
        session_response = {}
        session_response["intent"] = query.get_intent()
        session_response["data"] = sessionMGR.receive_query(query)
        return jsonify(session_response)
    except Exception as ex:
        print(ex)
        return jsonify({"response": "error in processing sent request"})

def setup():
	return [SessionMGR]



#Assume JSON is prepared before creating a query instance
class Query:
    def __init__(self, json_data):
        self.identifier = "a"
        self.json = json_data
        self.intent = self.json["intent"]["name"]
        self.entities = {}
        print(self.json)
        entity_list = self.json["entities"]
        print("Entity_list: {}".format(entity_list))
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
    def __init__(self, identity, args,fn):
        self.identifier = identity
        #self.cu
        self.completion_status = False
        self.chat_history = []
        self.arg_dict = args
        self.function = fn
        
    def process_query(self, query_object):
        entity_args = query_object.get_entities()
        print("Entities captured: {}".format(entity_args))
        for entity_type in entity_args.keys():
            entity_value = entity_args[entity_type]
            if (entity_type in self.arg_dict.keys() and self.arg_dict.get(entity_type,0) is None):
                self.arg_dict[entity_type] = entity_value
        #After filling the argument slots, check if all required arguments are flled
        print(self.arg_dict)
        if(None in self.arg_dict.values()):
            print("Missing values detected!")
            missing_parameters = [i for i in self.arg_dict.keys() if self.arg_dict[i] is None]
            reply = "Please specify the following parameters:"
            for i in missing_parameters:
                reply += " {},".format(i)
                reply = reply[:-1]
            print(reply)
            return reply
        #All arguments filled; proceed to call the function
        else:
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
    def terminate_session():
        return "terminate session"


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
        query_intent = query.get_intent()
        answer = None
        if(query_intent in self.args_required.keys()):
            arg_dict = self.args_required[query_intent]
            print(self.intent_functions)
            fn = self.intent_functions[query_intent]
            new_session = Session(identifier, arg_dict, fn)
            self.sessions[identifier] = new_session
            answer = new_session.process_query(query)
            return answer 
        else:
            #TODO: return an error message stating that intent could not be identified
            answer = "Error: intent not identified"
            return answer
            
    def receive_query(self,query):
        identifier = query.get_identifier()
        #If query identifier not in dictionary, create a new session, else process the query
        if(identifier not in self.sessions):
            answer = self.create_session(identifier, query)
            return answer 
        else:
            session = self.sessions[identifier]
            answer = session.process_query(query)
            # Check for completion
            # TODO: keep server in memory
            completion_status = session.get_completion_status()
            if(completion_status):
                self.remove_session(identifier)
            return answer
        
   
    def remove_session(self,identifier):
        # get Session to send termination message?
        del self.sessions[identifier]
        
def show_usage(resource):
    reply = "showing resource {}".format(resource)
    print(reply)
    return reply

def list_VM():
    print("Listing VMS")
    backend_IP = "202.183.76.61"
    reply = requests.get(url='http://{}/listallvms'.format(backend_IP)).json()
    print("Reply :", reply)
    return reply

args_required = {"show_usage":{"resource":None}, "list_VM":{}}
intent_function = {"show_usage": show_usage, "list_VM": list_VM}
sessionMGR = Session_Manager(args_required, intent_function)




