import os
import getpass
import platform

def check_system():
    version = platform.release().lower()
    if "microsoft" in version:
        return "wsl"
    if platform.system() == "Windows":
        return "windows_native"
    return "linux_native"


def get_path():
    ask_path = input("Voulez-vous entrer le chemin vers votre projet GNS3 manuellement ? (y/n) ")
    sys_type = check_system
    if ask_path == 'y':
        while True:
            raw_path = input("Veuillez entrer le chemin vers votre projet : ").strip()
            
            raw_path = raw_path.replace('"', '').replace("'", "")
            
            if sys_type == "wsl" and (raw_path.startswith("C:") or raw_path.startswith("D:")):
                drive = raw_path[0].lower() # récupère 'c' ou 'd'
                translated_path = raw_path.replace("\\", "/")
                project_path = re.sub(r'^[a-zA-Z]:', f'/mnt/{drive}', translated_path)
                print(f"Chemin Windows détecté, traduction pour WSL : {project_path}")
            else:
                project_path = raw_path

            if os.path.exists(project_path):
                break
            print(f"Erreur : Le chemin [{project_path}] n'existe pas. Réessayez.")
    else:
        project_name = input("Entrez le nom du projet : ")
        user = getpass.getuser()
        project_path = None

        if sys_type == "wsl":
            win_user = input(f"Nom d'utilisateur Windows (par défaut '{user}') : ") or user
            paths_to_check = [
                f"/mnt/c/Users/{win_user}/GNS3/projects/{project_name}",
                f"/mnt/d/Users/{win_user}/GNS3/projects/{project_name}"
            ]
        elif sys_type == "windows_native":
            paths_to_check = [
                f"C:/Users/{user}/GNS3/projects/{project_name}",
                f"D:/Users/{user}/GNS3/projects/{project_name}"
            ]
        else:
            paths_to_check = [f"/home/{user}/GNS3/projects/{project_name}"]

        for path in paths_to_check:
            if os.path.exists(path):
                project_path = path
                print("Project Path Valide ! ")
                break
        
        if not project_path:
            print("Chemin introuvable, veuillez relancer et/ou entrer le chemin manuellement.")

    return project_path

def trouver_fichier_config(dossier_router, nom_fichier):
    for racines, dirs, files in os.walk(dossier_router):
        if nom_fichier in files:
            return os.path.join(racines, nom_fichier)
        
project_path = get_path()
