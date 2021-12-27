def UserInputBool(message: str) -> bool:
  accepted_responces = ["n","N","y","Y"]
  user_responce = ""

  while user_responce not in accepted_responces:
    user_responce = input(message) or "N"
  
  if user_responce == "n" or user_responce == "N":
    return False
  else:
    return True
