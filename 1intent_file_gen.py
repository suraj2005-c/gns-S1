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
                        "redistribution": False, #pq
                    }
                },
                {
                    "nom": "OSPF",
                    "version": "OSPFv3",
                    "parametres": {
                        "area": 0, #expliquer aussi
                        "redistribution": False, # pq
                    }
                },
                {
                    "nom": "BGP",
                    "parametres": {
                        "next_hop_self": False, #expliquer
                        "redistribution": ["connected"], #expl
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
    rtr_global_id = 1
    for i in range(1, as_nb + 1):
        rtr_nb = int(input(f"Combien de routeurs pour l'AS {i} ? "))
        protocole = str.casefold(input(f"Quel protocole voulez-vous utiliser pour l'AS {i} ? "))

        for j in range(1,rtr_nb+1):
            data = add_rtr(rtr_global_id, i, protocole)
            add_loopback(data,protocole)
            neigh_list = ask_n_add_neigh(rtr_global_id, data)

            int_nb = len(neigh_list)
            for k in range(int_nb):
                add_interface(data, protocole, k+1)
            
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

def add_interface(rtr_data,protocole, indice):
    name = f"GigabitEthernet{indice}/0"
    rtr_data["interfaces"].append({
        "name": name,
        "ipv6": "",
        "protocole": [f"{protocole}"]
    })

def add_loopback(rtr_data, protocole):
    rtr_data["interfaces"].append({
        "name": "Loopback0",
        "ipv6" : "",
        "protocole":[f"{protocole}"]
    })

def ask_n_add_neigh(rtr_id, rtr_data):
    neigh_list = []
    interface = 1
    while True:
        print(f"Veuillez donner le nom d'un des voisins de R{rtr_id} dans le format suivant ex : 'R1', 'R3' etc.")
        print(f"S'il n'y a plus de voisins restants écrivez 'STOP' ")
        rout = input(f"Quels sont les voisins du routeur R{rtr_id} ? ")
        if (rout == "STOP"):
            break
        int= f"GigabitEthernet{interface}/0"
        neigh_list.append({
            "hostname": rout,
            "interface": int})
        interface = interface+1
    rtr_data["neighbors"].append(neigh_list)
    return neigh_list

if __name__ == '__main__':
    init()
