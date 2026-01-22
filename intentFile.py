# générateur de intent_file pour le Projet GNS3
import json

intent_file = open("intent_file.json", "w")


def initialisation_json(nb_as): #creation de dictionnaire
    data_f = {
             "as_numbers": [],
             "protocoles": [
                {
                    "nom": "RIP",
                    "version": "RIPng",
                    "parametres": {"redistribution": True}
                },
                {
                    "nom": "OSPF",
                    "version": "OSPFv3",
                    "parametres": {"area": 0, "redistribution": True}
                },
                {
                    "nom": "BGP",
                    "parametres": {
                        "next_hop_self": True,
                        "redistribution": ["connected"],
                        "update_source": "Loopback0"
                    }
                }
            ],
            "routeurs": []
        }
    
    for i in range(1,nb_as+1): #boucle qui cree le nb d'as demande par l'user et creer une liste ou on ajt
        data_f["as_numbers"].append({"asn": i, "name": f"AS{i}"})
    
    return data_f

def init():

    as_nb = int(input("Combien d'AS voulez vous ? ")) #demande nb as
    intent_file = initialisation_json(as_nb)
    rtr_global_id = 1
    for i in range(1, as_nb + 1):
        rtr_nb = int(input(f"Combien de routeurs pour l'AS {i} ? "))
        protocole = str.casefold(input(f"Quel protocole voulez-vous utiliser pour l'AS {i} ? "))

        for j in range(1,rtr_nb+1): #pour chaque routeur dans l'as
            data = add_rtr(rtr_global_id, i, protocole)  #initialise la structure du routeur
            add_loopback(data,protocole) #ajt l'interface loopback
            costs, external_intf = ask_n_add_neigh(rtr_global_id, data, protocole, i)

            # On récupère la liste des interfaces qui sont externes et le dico cost qui associe chaque num a son cout
            for interface_num , cost in costs.items(): #creer l'interface pour les voisins declares
                # Si l'interface est dans external_interfaces, on passe None au lieu du protocole
                current_proto = None if interface_num in external_intf else protocole
                add_interface(data, current_proto, interface_num, cost)
            
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
            "neighbors": [],
            "bgp_neighbors": []
         }
    return data  

def add_interface(rtr_data,protocole, indice,cost=None):
    name = f"GigabitEthernet{indice}/0"
    proto_list = [f"{protocole}"] if protocole else []
    interface_data = {"name": name, "ipv6": "", "protocole": proto_list}
    
    if protocole and protocole.lower() == "ospf" and cost is not None:
        interface_data["cost"] = cost
    rtr_data["interfaces"].append(interface_data)

def add_loopback(rtr_data, protocole):
    rtr_data["interfaces"].append({
        "name": "Loopback0",
        "ipv6" : "",
        "protocole":[f"{protocole}"]
    })

def ask_n_add_neigh(rtr_id, rtr_data,protocole, as_num):
    neigh_list = []
    interface = 1
    costs = {}
    external_interfaces = [] # Liste pour noter quelles interfaces sortent de l'AS
    while True:
        rout = input(f"Voisin du routeur R{rtr_id} (ou 'STOP') ? ")
        if (rout == "STOP"): break

        # demande l'as du voisin
        v_as = int(input(f"Quel est l'AS de {rout} ? "))
        if v_as != as_num:
            external_interfaces.append(interface)
        
        int_name = f"GigabitEthernet{interface}/0"
        cost = None
        # Demande le cout de ospf que si cest dans le meme as
        if protocole.lower() == "ospf" and v_as == as_num:
            cost = int(input(f"Quel est le coût OSPF pour l'interface vers {rout} ? "))
            costs[interface] = cost
        else:
            costs[interface] = None
        
        neigh_list.append({"hostname": rout, "interface": int_name})
        interface += 1
    rtr_data["neighbors"].append(neigh_list)
    return costs, external_interfaces

if __name__ == '__main__':
    init()
