#!/usr/bin/env python

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import sys
import os
import json

@Configuration()
class SequenceCommand(StreamingCommand):
    """ 

    ##Syntax


    ##Description


    ##Example


    """
    model = Option(
        doc='''
        **Syntax:** **model=<name>*
        **Description:** ''',
        require=True)
    counterexample = Option(
        doc='''
        **Syntax:** **counterexample=<True|False>*
        **Description:** ''',
        require=False,
	validate=validators.Boolean())

    def stream(self, events):

	model = self.model

	if not self.counterexample:
		counterexample = False
	else:
		counterexample = self.counterexample

        if len(self.fieldnames) > 0:
        	raise Exception("The sequence command takes no field arguments")

	try:
        	model_file = open("../default/data/statemodels.json","r")
        	modeldict = json.loads(model_file.read())
        	del model_file

	except:
        	raise Exception("State model failed to parse")

	if model not in modeldict:
		raise Exception("State model does not exist")

	models = {}

        for event in events:

		# check the scope (required fields) are met
        	counter = 0
        	for field in modeldict[model]["scope"]:
                	if field in event:
				if str(event[field]) != "":
                        		counter += 1

        	if counter != len(modeldict[model]["scope"]):
			yield event
                	continue

		# it would be better to use a cryptographic hash (md5?) for the key below
		# to ensure overlaps cannot occur, however that may introduce significantly
		# higher cycles - need to look more into this
        	key = ""
        	for field in modeldict[model]["scope"]:
                	key += str(event[field])

		# do we already have a finite-state machine for this event?
		if key in models:

			# the contents of the for loop below evaluate if a transition
			# is possible and if so change the state of the model

                	for transition in modeldict[model]["states"][models[key]["state"]]["transitions"]:
                        	holds = True
				try:
                        		for field in modeldict[model]["states"][models[key]["state"]]["transitions"][transition]["guard"]:
                                		# if the guard doesn't hold
                                		if str(event[field]) != modeldict[model]["states"][models[key]["state"]]["transitions"][transition]["guard"][field]:
                                        		holds = False

                        		if holds:
                                		# transition to next state
                                		models[key]["state"] = modeldict[model]["states"][models[key]["state"]]["transitions"][transition]["transition"]
                                		# increment depth
                                		models[key]["depth"] = int(models[key]["depth"]) + 1

						# provide counterexample if requested
						if counterexample:
                                      			models[key]["counterexample"] = models[key]["counterexample"] + "->" + str(models[key]["depth"]) + ":" + models[key]["state"]
				except:
					pass

				# update the event after evaluation above
                        	event["state"] = models[key]["state"]
                        	event["depth"] = models[key]["depth"]
				if counterexample:
                                	event["counterexample"] = models[key]["counterexample"]
                	yield event

        	else:

			# this for loop determines if a new finite-state machine
			# ough be created according to the model contraints and does so

                	for field in modeldict[model]["constraints"]:
                        	if event[field] != modeldict[model]["constraints"][field]:
                                	continue
                        	models[key] = {"state": "start", "depth": "0"}
                        	event["state"] = models[key]["state"]
                        	event["depth"] = models[key]["depth"]
				if counterexample:
					models[key]["counterexample"] = "0:start"
					event["counterexample"] = models[key]["counterexample"]
                        yield event

dispatch(SequenceCommand, sys.argv, sys.stdin, sys.stdout, __name__)
