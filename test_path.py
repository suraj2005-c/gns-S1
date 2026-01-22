import os
import getpass

ask_path = input("Voulez vous entrer le chemin vers votre projet GNS3 ? (y/n) ")
if (ask_path == 'y'):
    project_path = input("Veuillez entrer le chemin vers votre projet ")
else:
    project_name = input("Entrez le nom du projet : ")
    
    user = getpass.getuser()
    os_user = os.name

    if (os_user == 'posix'):
        project_path = f"/home/{user}/GNS3/projects/{project_name}"
    else:
        project_path = f"C:/User/{user}/GNS3/projects"

    
print(project_path)
