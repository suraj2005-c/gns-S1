import os
import getpass
import platform

def check_system():
    version = platform.release().lower()
    
    if "microsoft" in version:
        return "microsoft"
    return "Autre"

ask_path = input("Voulez vous entrer le chemin vers votre projet GNS3 ? (y/n) ")
if (ask_path == 'y'):
    project_path = input("Veuillez entrer le chemin vers votre projet ")
else:
    project_name = input("Entrez le nom du projet : ")
    
    user = getpass.getuser()
    os_user = os.name

    if (check_system() == "microsoft"):
        project_path = f"C:/User/{user}/GNS3/projects"
    else:
        project_path = f"/home/{user}/GNS3/projects/{project_name}"

    
print(project_path)
