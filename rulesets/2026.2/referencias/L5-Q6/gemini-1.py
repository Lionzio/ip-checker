# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L5-Q6, sem nenhum código de aluno. Revise antes do merge.
import sys

def cifra_cesar(texto, chave):
    resultado = []
    for char in texto:
        if char == ' ':
            continue
        codigo = ord(char)
        if 97 <= codigo <= 122:
            novo_codigo = (codigo - 97 - chave) % 26 + 97
            resultado.append(chr(novo_codigo))
        elif 65 <= codigo <= 90:
            novo_codigo = (codigo - 65 - chave) % 26 + 65
            resultado.append(chr(novo_codigo))
        else:
            resultado.append(char)
    return "".join(resultado)

def eh_primo(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def eh_quadrado_perfeito(n):
    if n <= 0:
        return False
    raiz = int(n**0.5)
    return raiz * raiz == n

def main():
    print("Boa noite a todos!! Sejam bem vindos ao reino de Cinland. A aventura será longa, mas a gloria é eterna!!")
    print("Vamos as apresentações.")
    print()

    while True:
        try:
            n = int(input())
        except EOFError:
            return
        if 1 <= n <= 4:
            break
        print("Não tem toda essa gente pra jogar não.")

    classes_map = {
        'B': 'Bardo',
        'G': 'Guerreiro',
        'L': 'Ladino',
        'M': 'Mago'
    }

    armas_lista = ["cajado", "machado grande", "adaga", "adaga dupla"]
    utilidades_lista = ["grimorio", "escudo de madeira", "alaude", "ferramentas de ladrao"]
    consumiveis_lista = ["pergaminho oculto", "racao de viagem", "pocao de cura", "bomba de fumaca"]

    aventureiros = []

    for _ in range(n):
        linha = input().split()
        nome = linha[0]
        sigla_classe = linha[1]
        nome_classe = classes_map[sigla_classe]
        
        inventario = {}
        while True:
            item_entrada = input()
            if item_entrada == "pronto":
                break
            partes = item_entrada.split(" - ")
            cifrado = partes[0]
            chave = int(partes[1])
            poder = int(partes[2])
            
            decifrado = cifra_cesar(cifrado, chave)
            
            tipo = "desconhecido"
            if decifrado in armas_lista:
                tipo = "arma"
            elif decifrado in utilidades_lista:
                tipo = "utilidade"
            elif decifrado in consumiveis_lista:
                tipo = "consumivel"
            
            inventario[decifrado] = {"tipo": tipo, "poder": poder}
            
        aventureiro = {
            "nome": nome,
            "classe": nome_classe,
            "sigla": sigla_classe,
            "inventario": inventario,
            "vivo": True
        }
        aventureiros.append(aventureiro)
        
        itens_str_list = []
        for k, v in inventario.items():
            itens_str_list.append(f"{k} [{v['tipo']}, {v['poder']}]")
        
        if itens_str_list:
            itens_str = ", ".join(itens_str_list)
            print(f"{nome} ({nome_classe}): {itens_str}")
        else:
            print(f"{nome} ({nome_classe}): sem itens")

    print("Grupo completamente apresentado, espero que todos estejam preparados para o que estar por vir.")
    print()

    print("Ao passa pelo arco de pedras, vocês encontram um lugar silencioso, com um odor nada agradável e um frio sem igual. Um calafrio na espinha os chama a recuar, mas a jornada começa aqui. Bem vindos a Dungeon do Grad5.")

    qt_linhas = int(input())
    matriz = []
    for _ in range(qt_linhas):
        matriz.append([int(x) for x in input().split()])

    linhas = len(matriz)
    cols = len(matriz[0])

    r, c = 0, 0
    caminho = [(0, 0)]
    visitados = {(0, 0)}

    while True:
        valor_atual = matriz[r][c]
        if valor_atual == 99:
            break
        
        vizinhos = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < linhas and 0 <= nc < cols:
                if (nr, nc) not in visitados:
                    vizinhos.append((matriz[nr][nc], nr, nc))
        
        if not vizinhos:
            break
        
        vizinhos.sort(key=lambda x: x[0], reverse=True)
        _, nr, nc = vizinhos[0]
        r, c = nr, nc
        caminho.append((r, c))
        visitados.add((r, c))

    morto_por_beholder = False

    for idx_passo, (rr, cc) in enumerate(caminho):
        val = matriz[rr][cc]
        if val == 0:
            tipo_sala = "Entrada"
        elif val == 99:
            tipo_sala = "Saída"
        elif eh_primo(val):
            tipo_sala = "Armadilha"
        elif eh_quadrado_perfeito(val):
            tipo_sala = "Looting"
        else:
            tipo_sala = "Sala Comum"
        
        print(f"Casa visitada: {tipo_sala}")

        vivos = [av for av in aventureiros if av["vivo"]]
        if not vivos:
            break

        if tipo_sala == "Armadilha":
            tipo_armadilha = input()
            if tipo_armadilha == "flechas":
                guerreiro = next((av for av in vivos if av["classe"] == "Guerreiro"), None)
                if guerreiro and "escudo de madeira" in guerreiro["inventario"]:
                    del guerreiro["inventario"]["escudo de madeira"]
                    print(f"O escudo de madeira de {guerreiro['nome']} protegeu o grupo.")
                else:
                    vitima = vivos[-1]
                    vitima["vivo"] = False
                    print(f"{vitima['nome']} sacrificou-se pelo grupo.")
                    
                    bardo = next((av for av in vivos if av["classe"] == "Bardo" and av["vivo"]), None)
                    if bardo and "pocao de cura" in bardo["inventario"]:
                        del bardo["inventario"]["pocao de cura"]
                        vitima["vivo"] = True
                        print(f"{bardo['nome']} usou a pocao de cura e salvou {vitima['nome']}.")
            elif tipo_armadilha == "beholder":
                ladino = next((av for av in vivos if av["classe"] == "Ladino"), None)
                if ladino and "bomba de fumaca" in ladino["inventario"]:
                    del ladino["inventario"]["bomba de fumaca"]
                    print(f"{ladino['nome']} usou a bomba de fumaça e o escaparam do Beholder.")
                else:
                    print("Entraram em uma sala que não deveriam. A ultima visão é tudo ficando vermelho e em um flash, tudo fica preto. Vocês tão mortos.")
                    morto_por_beholder = True
                    for av in aventureiros:
                        av["vivo"] = False
                    break

        elif tipo_sala == "Looting":
            print("Finalmente um descanso! Aproveitam as maravilhas presentes na sala.")
            vivos_atuais = sorted([av for av in aventureiros if av["vivo"]], key=lambda x: x["sigla"])
            ladino = next((av for av in vivos_atuais if av["classe"] == "Ladino"), None)
            
            tem_ferramentas = False
            if ladino and "ferramentas de ladrao" in ladino["inventario"]:
                tem_ferramentas = True
                del ladino["inventario"]["ferramentas de ladrao"]
                print(f"{ladino['nome']} arrombou o baú trancado!")

            num_itens = 2 if tem_ferramentas else 1
            for _ in range(num_itens):
                entrada_loot = input().split(" - ")
                item_esp = entrada_loot[0]
                cod = int(entrada_loot[1])
                
                vivos_atuais = sorted([av for av in aventureiros if av["vivo"]], key=lambda x: x["sigla"])
                target_idx = cod % len(vivos_atuais)
                destinatario = vivos_atuais[target_idx]
                
                print(f"{item_esp} foi para {destinatario['nome']} ({destinatario['classe']}).")
                
                classe_ideal = {
                    "lira encantada": "Bardo",
                    "martelo do trovao": "Guerreiro",
                    "olho do abismo": "Ladino",
                    "orbe arcano": "Mago"
                }
                
                eh_ideal = (classe_ideal.get(item_esp) == destinatario["classe"])
                
                if eh_ideal:
                    print("O poder que esta em suas mãos é grandioso e parece chamar-lhe a glória eterna.")
                    for it_name, it_info in destinatario["inventario"].items():
                        it_info["poder"] *= 2
                else:
                    print("O poder é grande demais, você não consegue extrair o máximo dele.")
                    for it_name, it_info in destinatario["inventario"].items():
                        it_info["poder"] = int(it_info["poder"] * 1.25)
                        
                tipo_item = "utilidade"
                destinatario["inventario"][item_esp] = {"tipo": tipo_item, "poder": 0}

    vivos_finais = [av for av in aventureiros if av["vivo"]]

    print()
    if not vivos_finais or morto_por_beholder:
        print("Os sonhos e objetivos de todos são deixados no chão do Grad5. Nenhum de vocês restou. A glória nunca será alcançada!")
        return
    else:
        print("Vocês finalmente saem das cavernas escuras e frias. Mas não parece chegar em um lugar melhor.")

    print()
    print("O lugar é silencioso. Até que, de repente, um rugido é ouvido. Uma criatura surge das sombras: o temido TarraByte!")

    boss_info = input().split()
    hp_monstro = int(boss_info[0])
    ca_monstro = int(boss_info[1])

    iniciativas = []
    for av in vivos_finais:
        in_at = input().split()
        iniciativa = int(in_at[0])
        ataque_rolagem = int(in_at[1])
        iniciativas.append({
            "av": av,
            "iniciativa": iniciativa,
            "ataque": ataque_rolagem
        })

    iniciativas.sort(key=lambda x: (-x["iniciativa"], aventureiros.index(x["av"])))

    nomes_ordem = [item["av"]["nome"] for item in iniciativas]
    print(f"Ordem de iniciativa: {', '.join(nomes_ordem)}")

    bardo_inspirou = False
    boss_morto = False

    for item in iniciativas:
        av = item["av"]
        iniciativa = item["iniciativa"]
        rolagem_base = item["ataque"]
        
        if av["classe"] == "Bardo" and "alaude" in av["inventario"]:
            print(f"{av['nome']} inspirou o grupo.")
            bardo_inspirou = True
            continue
            
        bonus_ataque = 0
        if bardo_inspirou and av["classe"] in ["Guerreiro", "Ladino"]:
            bonus_ataque = 2
            
        rolagem_total = rolagem_base + bonus_ataque
        
        arma_poder = 0
        for it_name, it_info in av["inventario"].items():
            if it_info["tipo"] == "arma":
                if it_info["poder"] > arma_poder:
                    arma_poder = it_info["poder"]
                    
        dano = arma_poder
        
        if av["classe"] == "Mago" and "pergaminho oculto" in av["inventario"]:
            dano += av["inventario"]["pergaminho oculto"]["poder"]
            del av["inventario"]["pergaminho oculto"]
        elif av["classe"] == "Guerreiro" and "racao de viagem" in av["inventario"]:
            dano += av["inventario"]["racao de viagem"]["poder"]
            del av["inventario"]["racao de viagem"]
            
        is_critico = (rolagem_base == 20)
        acertou = is_critico or (rolagem_total >= ca_monstro)
        
        if acertou:
            if is_critico:
                dano *= 2
                hp_monstro -= dano
                print(f"{av['nome']} acertou um critico e causou {dano} de dano.")
            else:
                hp_monstro -= dano
                print(f"{av['nome']} acertou e causou {dano} de dano.")
                
            if hp_monstro <= 0:
                boss_morto = True
                print(f"O TarraByte foi derrotado por {av['nome']}!")
                break
        else:
            print(f"{av['nome']} errou o ataque.")

    if not boss_morto:
        print(f"O TarraByte sobreviveu com {hp_monstro} de HP e obliterou o grupo. Fim da aventura.")

if __name__ == "__main__":
    main()
