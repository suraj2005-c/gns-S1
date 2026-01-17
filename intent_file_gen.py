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
                        "redistribution": True, #pq
                    }
                },
                {
                    "nom": "OSPF",
                    "version": "OSPFv3",
                    "parametres": {
                        "area": 0,
                        "redistribution": False, # pq
                    }
                },
                {
                    "nom": "BGP",
                    "parametres": {
                        "next_hop_self": False, #expliquer
                        "redistribution": ["connected", "static"], #expl
                        "update_source": "Loopback0" #expli
                    }
                }
            ],
            "routeurs": []
        }
    
    for i in range(1,nb_as+1):
        data_f["as_numbers"].append({"asn": i, "name": f"AS{i}"})
    
    return data_f

def init():

    as_nb = int(input("Combien d'AS voulez vous ? "))
    intent_file = initialisation_json(as_nb)
    rtr_global_id = 0
    for i in range(1, as_nb + 1):
        rtr_nb = int(input(f"Combien de routeurs pour l'AS {i} ? "))
        protocole = str.casefold(input(f"Quel protocole voulez-vous utiliser pour l'AS {i} ? "))

        for j in range(1,rtr_nb+1):
            data = add_rtr(rtr_global_id, i, protocole)
            int_nb = int(input(f"Configurez un nombre d'interfaces pour le routeur R{rtr_global_id} : "))
            for k in range(int_nb):
                add_interface(data, protocole)
            
            intent_file["routeurs"].append(data)
            rtr_global_id += 1

    with open("intent_file.json", "w", encoding="utf-8") as f:
        json.dump(intent_file, f, indent=4)
    print("\nL'intent_file.json a été généré. ")


def add_rtr(rtr_global_id, as_num, protocole):
    print("Ajout de routeur : ")
    data ={
            "hostname": f"R{rtr_global_id}",
            "asn": as_num,
            "interfaces": [],
            "bgp_neighbors": []
         }
    return data  

def add_interface(rtr_data,protocole):
    name = input("Ajouter une interface (ex: FastEthernet0/0 GigaEthernet1/0) : ")
    ipv6 = input("Adresse IPv6 : ")
    rtr_data["interfaces"].append({
        "name": name,
        "ipv6": ipv6,
        "protocole": [f"{protocole}"]
    })

def add_bgp_neighbor(neigh_address, neigh_as, rtr_data):
    print("Ajout des voisins BGP")
    rtr_data["bgp_neighbors"].append(
        {"ip": f"{neigh_address}", "remote_as": neigh_as}
    )

if __name__ == '__main__':
    init()
