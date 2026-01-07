# générateur de intent_file pour le Projet GNS3



def init():

    as_nb = int(input("Combien d'AS voulez vous ? "))

    for i in range(as_nb):
        rtr_nb = int(input(f"Combien de routeurs pour l'AS {i} ?"))
        protocole = str.casefold(input(f"Quel protocole voulez-vous utiliser pour l'AS {i} ?"))

        for j in range(rtr_nb):
            add_rtr(as_nb,j,protocole)
            int_nb = int(input(f"Configurez un nombre d'interfaces pour le routeur :  {j} ?"))
            for k in range(int_nb):
                add_interface(j)


def add_rtr(as_nb, rtr_id, protocole):
    print("Ajout de routeur :")


def add_interface(rtr_id):
    print("Ajout d'interface")


init()