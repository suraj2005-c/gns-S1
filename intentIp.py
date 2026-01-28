import json
import os

def inject_ips_into_intent():
    intent_file="intent_file.json"

    if not os.path.exists(intent_file):
        print(f"Erreur: {intent_file} n'existe pas.")
        return
    
    with open(intent_file, 'r') as file:
        data=json.load(file)

    plages=data.get("plages_ip", {}) # Récupère les plages d'IP
    prefixe_physiques=plages["physiques"] # prefixes ip liens physiques
    prefixe_loopback=plages["loopback"] #prefixes ip loopback
    routeurs=data.get("routeurs", [])
    routeurs_map={r['hostname']: r for r in routeurs}

    processed_links=set() #on utilise un ensemblle pour eviter les doublons

    for r in routeurs: # pour chaque routeur
        id=int(r['hostname'][1:]) #on extrait son id
        hostname=r['hostname'] # nom du routeur

        ip_loopback=f"{prefixe_loopback}::{id}/128" # on genere l ip loopback
        for intf in r['interfaces']: # on parcourt les interfaces
            if "Loopback" in intf['name']: # si c est la loopback
                intf['ipv6']=ip_loopback # on assigne l ip loopback

        if 'bgp_neighbors' in r:# si le routeur a des bgp_neighbors
            r['router_id']=f"{id}.{id}.{id}.{id}" # on assigne le router id
            r['networks']=[ip_loopback] # on ajoute le loopback aux networks
        
        if 'neighbors' in r :# si le routeur a des voisins
            for neigh_group in r['neighbors']:# pour chaque groupe de voisins
                for n in neigh_group:
                    neighbor_name=n['hostname'] # nom du voisin
                    local_intf_name=n['interface'] # interface locale utilisée

                    if neighbor_name and neighbor_name in routeurs_map: # si le voisin existe dans la map
                        n_id=int(neighbor_name[1:]) # on extrait son id
                        id_lien=sorted([id,n_id]) #on cree un id pour le lien 
                        cle_lien=tuple(sorted([hostname, neighbor_name])) # cle unique pour le lien

                        if cle_lien not in processed_links: # si le lien n a pas encore été traité
                            processed_links.add(cle_lien)# on le marque comme traité
                            indice_lien=f"{id_lien[0]}{id_lien[1]}" # on genere un indice pour le lien
                            prefixe_lien=f"{prefixe_physiques}:{indice_lien}" # on genere le prefixe ip du lien
                            
                            local_intf_obj = next((i for i in r['interfaces'] if i['name'] == local_intf_name), None) # on trouve l objet interface locale

                            neighbor_r=routeurs_map[neighbor_name] # on récupère l objet routeur du voisin
                            neighbor_intf_obj= None

                            if neighbor_r.get('neighbors'): # on vérifie que le voisin a des voisins
                                for nb_groupe in neighbor_r['neighbors']: # on parcourt les groupes de voisins du voisin
                                    for nb_item in nb_groupe: # on parcourt les items du groupe
                                        if nb_item['hostname']== hostname: # si on trouve le routeur local comme voisin
                                            nom_intf_cible=nb_item['interface'] # on récupère le nom de l interface cible
                                            neighbor_intf_obj=next(i for i in neighbor_r['interfaces'] if i['name']== nom_intf_cible) # on trouve l objet interface du voisin
                            
                            if local_intf_obj and neighbor_intf_obj: # si on a bien les deux objets interfaces
                                if id<n_id: # on assigne les ips en fonction des ids
                                    local_intf_obj['ipv6']=f"{prefixe_lien}::1/64"
                                    neighbor_intf_obj['ipv6']=f"{prefixe_lien}::2/64"
                                else:
                                    local_intf_obj['ipv6']=f"{prefixe_lien}::2/64"
                                    neighbor_intf_obj['ipv6']=f"{prefixe_lien}::1/64"

    as_routeurs={} # dictionnaire pour stocker les routeurs par ASn
    for r in routeurs: # pour chaque routeur
        asn=r['asn'] # on récupère son ASn
        if asn not in as_routeurs: # si l ASn n est pas encore dans le dictionnaire
            as_routeurs[asn]=[] # on initialise une liste pour cet ASn
        as_routeurs[asn].append(r)# on ajoute le routeur à la liste de son ASn

        if 'bgp_neighbors' in r: # si le routeur a des bgp_neighbors
            r['bgp_neighbors']=[] # on vide la liste pour la reconstruire

    for r in routeurs: 
        asn_r = r['asn'] # on récupère son ASn
        id_r=int(r['hostname'][1:]) # on extrait son id
        for paire in as_routeurs[asn_r]: # pour chaque routeur dans le même AS
            if paire['hostname']!=r['hostname']: # si ce n est pas lui-même
                id_paire=int(paire['hostname'][1:]) # on extrait l id du paire
                loopback_paire=f"{prefixe_loopback}::{id_paire}" # on génère l ip loopback du paire
                r['bgp_neighbors'].append({
                    'ip': loopback_paire,
                    'remote_as':asn_r
                })
                
        if 'neighbors' in r : # si le routeur a des voisins
            for neigh_groupe in r['neighbors']: 
                for n in neigh_groupe:
                    neighbor_name=n['hostname'] # nom du voisin
                    if neighbor_name in routeurs_map: # si le voisin existe dans la map
                        neighbor_r=routeurs_map[neighbor_name] #on recupere le nom du voisin

                        if neighbor_r['asn']!=r['asn']: # si le voisin est dans un AS different
                            nom_intf_cible=None
                            for nb_groupe in neighbor_r['neighbors']:
                                for nb_item in nb_groupe:
                                    if nb_item['hostname']== r['hostname']:
                                        nom_intf_cible=nb_item['interface'] # on récupère le nom de l interface cible                   
                
                            if nom_intf_cible:# on vérifie qu on a bien le nom de l interface cible
                                intf_neighbor=next((i for i in neighbor_r['interfaces'] if i['name']==nom_intf_cible), None)
                                if intf_neighbor and 'ipv6' in intf_neighbor:
                                    ip_neighbor=intf_neighbor['ipv6'].split('/')[0] #on recupere l ip sans le prefixe
                                    rel = relation(r['hostname'], neighbor_name, neighbor_r['asn'])
                                    
                                    if rel == "STOP":
                                        continue # On saute ce voisin si STOP
                                    # On récupère les infos de politique
                                    policy_infos = addPolicies(r['asn'], rel)

                                    # On crée l'objet FINAL fusionné
                                    neighbor_info = {
                                        'ip': ip_neighbor,
                                        'remote_as': neighbor_r['asn']
                                    }
                                    # On ajoute les clés de la politique dans l'objet voisin
                                    neighbor_info.update(policy_infos)

                                    # 4. On ajoute le tout dans la liste en UNE fois
                                    r['bgp_neighbors'].append(neighbor_info)


        with open(intent_file,'w') as f:
            json.dump(data,f,indent=4)

    print(f"\nSuccess. {intent_file} a été modifié.")


def get_community(asn, relationship): # on assigne les communautés BGP en fonction des relationships
    if relationship == "customer":
        return f"{asn}:100"
    elif relationship == "peer":
        return f"{asn}:200"
    elif relationship == "provider":
        return f"{asn}:300"
    return None


def relation(r_name, neighbor_name, neighbor_as): # fonction pour demander la relationship entre deux routeurs
    
    while True:
        print(f"\n[BGP] Configuration de {neighbor_name} vu par {r_name} (AS {neighbor_as})")
        relationship = input("Relationship? (ex : 'peer', 'provider', 'customer') ou STOP : ")
        if relationship == "STOP":
            return "STOP"
        elif relationship in ["peer", "provider", "customer"]:
            return relationship
        else:
            print("relationship unknown. Please enter 'peer', 'provider', 'customer' or 'STOP'.")

def addPolicies(asn, relationship):
         
        if relationship=="provider":
            data = {}
            local_pref_value = 50
            data={
                "relationship" : relationship,
                "local_pref_val": local_pref_value,
                "community": get_community(asn, relationship)
            }
        elif relationship=="customer":
                local_pref_value = 200
                data={
                "relationship" : relationship,
                "local_pref_val": local_pref_value,
                "community": get_community(asn, relationship)
                }
        elif relationship=="peer":
                local_pref_value = 100
                data={
                    "relationship" : relationship,
                    "local_pref_val": local_pref_value,
                    "community": get_community(asn, relationship)
                }   
        

        else:
            print("relationship unknown. Please enter 'peer', 'provider', 'customer' or 'STOP'.")
        return data


if __name__ == "__main__":
    inject_ips_into_intent()    

    
