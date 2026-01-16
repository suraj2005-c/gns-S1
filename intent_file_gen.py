# générateur de intent_file pour le Projet GNS3
import json

intent_file = open("intent_file.json", "w")


def initialisation_json(nb_as):
    data_f = {
             "as_numbers": [],
             "protocoles": [
                {
                    "nom": "RIP",
                    "version": "RIPng",
                    "parametres": {
                        "redistribution": True,
                        "default_information_originate": False
                    }
                },
                {
                    "nom": "OSPF",
                    "version": "OSPFv3",
                    "parametres": {
                        "area": 0,
                        "redistribution": False,
                        "default_information_originate": False
                    }
                },
                {
                    "nom": "BGP",
                    "parametres": {
                        "next_hop_self": False,
                        "redistribution": ["connected", "static"],
                        "update_source": "Loopback0"
                    }
                }
            ],
            "routeurs": []
        }
    
    for i in range(1,nb_as):
        data_f["as_numbers"].append({"asn": i, "name": f"AS{i}"})
    
    return data_f

def init():

    as_nb = int(input("Combien d'AS voulez vous ? "))
    intent_file = initialisation_json(as_nb)

    for i in range(as_nb):
        rtr_nb = int(input(f"Combien de routeurs pour l'AS {i} ? "))
        protocole = str.casefold(input(f"Quel protocole voulez-vous utiliser pour l'AS {i} ? "))

        for j in range(rtr_nb):
            data = add_rtr(as_nb,j,protocole)
            int_nb = int(input(f"Configurez un nombre d'interfaces pour le routeur :  {j} ? "))
            for k in range(int_nb):
                add_interface(data, protocole)
            
            intent_file["routeurs"].append(data)

    with open("intent_file.json", "w", encoding="utf-8") as f:
        json.dump(intent_file, f, indent=4)
    print("\nL'intent_file.json a été généré. ")


def add_rtr(as_nb, rtr_id, protocole):
    print("Ajout de routeur : ")
    data ={
            "hostname": f"R{rtr_id}",
            "asn": as_nb,
            "interfaces": [],
            "bgp_neighbors": []
         }
    return data  

def add_interface(rtr_data,protocole):
    name = input("Nom de l'interface (ex: FastEthernet0/0 GigaEthernet1/0) : ")
    ipv6 = input("Adresse IPv6/Masque : ")
    rtr_data["interfaces"].append({
        "name": name,
        "ipv6": ipv6,
        "protocole": [f"{protocole}"]
    })

def add_bgp_neighbor(neigh_address, neigh_as, interface):
    print("Ajout des voisins BGP")


if __name__ == '__main__':
    init()
