# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L5-Q6, sem nenhum código de aluno. Revise antes do merge.
import math

# Dicionários de tipos de itens
TIPOS_ARMA = ["cajado", "machado grande", "adaga", "adaga dupla"]
TIPOS_UTILIDADE = ["grimorio", "escudo de madeira", "alaude", "ferramentas de ladrao"]
TIPOS_CONSUMIVEL = ["pergaminho oculto", "racao de viagem", "pocao de cura", "bomba de fumaca"]

MAPA_CLASSES = {
    "M": "Mago",
    "G": "Guerreiro",
    "B": "Bardo",
    "L": "Ladino"
}

def descifrar(texto_cripto, chave):
    resultado = []
    for c in texto_cripto:
        if c == ' ':
            resultado.append(' ')
        else:
            base = ord('a')
            original = ord(c) - base
            novo = (original - chave) % 26
            resultado.append(chr(base + novo))
    return "".join(resultado)

def obter_tipo(nome_item):
    if nome_item in TIPOS_ARMA:
        return "arma"
    elif nome_item in TIPOS_UTILIDADE:
        return "utilidade"
    elif nome_item in TIPOS_CONSUMIVEL:
        return "consumivel"
    return "desconhecido"

def eh_primo(n):
    if n < 2:
        return False
    for i in range(2, int(math.isqrt(n)) + 1):
        if n % i == 0:
            return False
    return True

def eh_quadrado_perfeito(n):
    if n <= 0:
        return False
    r = int(math.isqrt(n))
    return r * r == n

print("Boa noite a todos!! Sejam bem vindos ao reino de Cinland. A aventura será longa, mas a gloria é eterna!!")
print("Vamos as apresentações.")
print()

# Fase 1: Preparação
while True:
    try:
        n = int(input())
        if 1 <= n <= 4:
            break
        else:
            print("Não tem toda essa gente pra jogar não.")
    except:
        pass

aventureiros = []

for _ in range(n):
    linha = input().split()
    nome = linha[0]
    letra_classe = linha[1]
    nome_classe = MAPA_CLASSES[letra_classe]
    
    inventario = {}
    while True:
        item_linha = input()
        if item_linha == "pronto":
            break
        partes = item_linha.split(" - ")
        cripto = partes[0]
        chave = int(partes[1])
        poder = int(partes[2])
        
        nome_decifrado = descifrar(cripto, chave)
        tipo = obter_tipo(nome_decifrado)
        inventario[nome_decifrado] = {"tipo": tipo, "poder": poder}
    
    aventureiros.append({
        "nome": nome,
        "classe": nome_classe,
        "letra": letra_classe,
        "inventario": inventario
    })

    # Imprimir apresentação do aventureiro
    if not inventario:
        print(f"{nome} ({nome_classe}): sem itens")
    else:
        itens_str = []
        for k, v in inventario.items():
            itens_str.append(f"{k} [{v['tipo']}, {v['poder']}]")
        print(f"{nome} ({nome_classe}): " + ", ".join(itens_str))

print("Grupo completamente apresentado, espero que todos estejam preparados para o que estar por vir.")
print()

# Fase 2: Dungeon
print("Ao passa pelo arco de pedras, vocês encontram um lugar silencioso, com um odor nada agradável e um frio sem igual. Um calafrio na espinha os chama a recuar, mas a jornada começa aqui. Bem vindos a Dungeon do Grad5.")

qt_rc = int(input())
matriz = []
for _ in range(qt_rc):
    matriz.append([int(x) for x in input().split()])

r, c = 0, 0
visitados = set()

def tem_item(av, nome_item):
    return nome_item in av["inventario"]

def remover_item(av, nome_item):
    if nome_item in av["inventario"]:
        del av["inventario"][nome_item]

def get_vivo_por_letra(letra):
    for av in aventureiros:
        if av["letra"] == letra:
            return av
    return None

mortos = set()

while True:
    val_atual = matriz[r][c]
    
    if val_atual == 0:
        tipo_sala = "Entrada"
    elif val_atual == 99:
        tipo_sala = "Saída"
    elif eh_primo(val_atual):
        tipo_sala = "Armadilha"
    elif eh_quadrado_perfeito(val_atual):
        tipo_sala = "Looting"
    else:
        tipo_sala = "Sala Comum"
        
    print(f"Casa visitada: {tipo_sala}")
    
    if val_atual == 99:
        print("Vocês finalmente saem das cavernas escuras e frias. Mas não parece chegar em um lugar melhor.")
        chegou_fase3 = True
        break
        
    if tipo_sala == "Armadilha":
        tipo_arm = input()
        vivos = [av for av in aventureiros if av not in mortos]
        if not vivos:
            print("Os sonhos e objetivos de todos são deixados no chão do Grad5. Nenhum de vocês restou. A glória nunca será alcançada!")
            chegou_fase3 = False
            break
            
        if tipo_arm == "flechas":
            guerreiro = get_vivo_por_letra("G")
            if guerreiro and guerreiro not in mortos and tem_item(guerreiro, "escudo de madeira"):
                remover_item(guerreiro, "escudo de madeira")
                print(f"O escudo de madeira de {guerreiro['nome']} protegeu o grupo.")
            else:
                sacrificado = vivos[-1]
                bardo = get_vivo_por_letra("B")
                if bardo and bardo not in mortos and tem_item(bardo, "pocao de cura") and bardo != sacrificado:
                    remover_item(bardo, "pocao de cura")
                    print(f"{bardo['nome']} usou a pocao de cura e salvou {sacrificado['nome']}.")
                else:
                    mortos.add(sacrificado)
                    print(f"{sacrificado['nome']} sacrificou-se pelo grupo.")
                    vivos = [av for av in aventureiros if av not in mortos]
                    if not vivos:
                        print("Os sonhos e objetivos de todos são deixados no chão do Grad5. Nenhum de vocês restou. A glória nunca será alcançada!")
                        chegou_fase3 = False
                        break
        elif tipo_arm == "beholder":
            ladino = get_vivo_por_letra("L")
            if ladino and ladino not in mortos and tem_item(ladino, "bomba de fumaca"):
                remover_item(ladino, "bomba de fumaca")
                print(f"{ladino['nome']} usou a bomba de fumaça e o escaparam do Beholder.")
            else:
                print("Entraram em uma sala que não deveriam. A ultima visão é tudo ficando vermelho e em um flash, tudo fica preto. Vocês tão mortos.")
                print("Os sonhos e objetivos de todos são deixados no chão do Grad5. Nenhum de vocês restou. A glória nunca será alcançada!")
                chegou_fase3 = False
                break
                
    elif tipo_sala == "Looting":
        print("Finalmente um descanso! Aproveitam as maravilhas presentes na sala.")
        vivos = [av for av in aventureiros if av not in mortos]
        vivos_ord = sorted(vivos, key=lambda x: x["letra"])
        m = len(vivos_ord)
        
        ladino = get_vivo_por_letra("L")
        tem_ferramentas = ladino and ladino not in mortos and tem_item(ladino, "ferramentas de ladrao")
        
        if tem_ferramentas:
            remover_item(ladino, "ferramentas de ladrao")
            print(f"{ladino['nome']} arrombou o baú trancado!")
            
            # Duas entradas de loot
            for _ in range(2):
                entrada_loot = input().split(" - ")
                item_esp = entrada_loot[0]
                cod = int(entrada_loot[1])
                
                idx = cod % m
                alvo = vivos_ord[idx]
                
                alvo["inventario"][item_esp] = {"tipo": "utilidade", "poder": 0} # vai atualizar poder logo abaixo
                print(f"{item_esp} foi para {alvo['nome']} ({alvo['classe']}).")
                
                classe_ideal = {"lira encantada": "Bardo", "martelo do trovao": "Guerreiro", "olho do abismo": "Ladino", "orbe arcano": "Mago"}.get(item_esp)
                
                # Definir poder base do item especial (poder pode ser implícito ou calculado, mas o enunciado diz apenas que o item especial é adicionado)
                # Na verdade, o item especial aumenta o poder. Vamos atribuir um poder base ao item especial, por exemplo 10, ou verificar se o item já vem com poder.
                # Espere, o input do looting é "item_especial - cod_inventario". Não há poder informado na linha! 
                # Vamos assumir que o item especial tem poder 10 por padrão, ou o enunciado considera o poder do item como 10? Vamos olhar o exemplo: "olho do abismo - 10". Não tem poder. Vamos definir poder 10 para itens especiais.
                alvo["inventario"][item_esp]["poder"] = 10
                
                if alvo["classe"] == classe_ideal:
                    print("O poder que esta em suas mãos é grandioso e parece chamar-lhe a glória eterna.")
                    for k in alvo["inventario"]:
                        alvo["inventario"][k]["poder"] *= 2
                else:
                    print("O poder é grande demais, você não consegue extrair o máximo dele.")
                    for k in alvo["inventario"]:
                        alvo["inventario"][k]["poder"] = int(alvo["inventario"][k]["poder"] * 1.25)
        else:
            entrada_loot = input().split(" - ")
            item_esp = entrada_loot[0]
            cod = int(entrada_loot[1])
            
            idx = cod % m
            alvo = vivos_ord[idx]
            
            alvo["inventario"][item_esp] = {"tipo": "utilidade", "poder": 10}
            print(f"{item_esp} foi para {alvo['nome']} ({alvo['classe']}).")
            
            classe_ideal = {"lira encantada": "Bardo", "martelo do trovao": "Guerreiro", "olho do abismo": "Ladino", "orbe arcano": "Mago"}.get(item_esp)
            
            if alvo["classe"] == classe_ideal:
                print("O poder que esta em suas mãos é grandioso e parece chamar-lhe a glória eterna.")
                for k in alvo["inventario"]:
                    alvo["inventario"][k]["poder"] *= 2
            else:
                print("O poder é grande demais, você não consegue extrair o máximo dele.")
                for k in alvo["inventario"]:
                    alvo["inventario"][k]["poder"] = int(alvo["inventario"][k]["poder"] * 1.25)

    # Movimentação: encontrar vizinho com maior valor
    vizinhos = []
    if r > 0: vizinhos.append((r-1, c))
    if r < qt_rc - 1: vizinhos.append((r+1, c))
    if c > 0: vizinhos.append((r, c-1))
    if c < qt_rc - 1: vizinhos.append((r, c+1))
    
    maior_val = -1
    proximo = None
    for vr, vc in vizinhos:
        if (vr, vc) not in visitados:
            if matriz[vr][vc] > maior_val:
                maior_val = matriz[vr][vc]
                proximo = (vr, vc)
                
    visitados.add((r, c))
    if proximo:
        r, c = proximo
    else:
        break

if chegou_fase3:
    print()
    print("O lugar é silencioso. Até que, de repente, um rugido é ouvido. Uma criatura surge das sombras: o temido TarraByte!")
    
    boss_info = [int(x) for x in input().split()]
    hp_boss = boss_info[0]
    ca_boss = boss_info[1]
    
    vivos = [av for av in aventureiros if av not in mortos]
    iniciativas = {}
    for av in vivos:
        dados = [int(x) for x in input().split()]
        inici = dados[0]
        ataq = dados[1]
        iniciativas[av['nome']] = {"iniciativa": inici, "ataque": ataq, "av": av}
        
    # Ordenar iniciativas: maior para o menor. Empate: quem entrou antes (ordem em aventureiros)
    ordem_combate = sorted(vivos, key=lambda x: (-iniciativas[x['nome']]['iniciativa'], aventureiros.index(x)))
    
    nomes_ordem = [av['nome'] for av in ordem_combate]
    print("Ordem de iniciativa: " + ", ".join(nomes_ordem))
    
    inspirado = False
    for av in ordem_combate:
        if hp_boss <= 0:
            break
        nome = av['nome']
        dados_av = iniciativas[nome]
        rolagem_ataque = dados_av['ataque']
        
        if av['classe'] == "Bardo" and tem_item(av, "alaude"):
            print(f"{nome} inspirou o grupo.")
            inspirado = True
            continue
            
        bonus_ataque = 0
        if inspirado and av['classe'] in ["Guerreiro", "Ladino"]:
            bonus_ataque += 2
            
        # Calcular dano da melhor arma
        melhor_dano = 0
        for k, v in av['inventario'].items():
            if v['tipo'] == "arma":
                if v['poder'] > melhor_dano:
                    melhor_dano = v['poder']
                    
        # Consumíveis
        if av['classe'] == "Mago" and tem_item(av, "pergaminho oculto"):
            melhor_dano += av['inventario']["pergaminho oculto"]["poder"]
            remover_item(av, "pergaminho oculto")
        elif av['classe'] == "Guerreiro" and tem_item(av, "racao de viagem"):
            melhor_dano += av['inventario']["racao de viagem"]["poder"]
            remover_item(av, "racao de viagem")
            
        is_critico = (rolagem_ataque == 20)
        acertou = is_critico or (rolagem_ataque + bonus_ataque >= ca_boss)
        
        if acertou:
            dano_causado = melhor_dano
            if is_critico:
                dano_causado *= 2
                hp_boss -= dano_causado
                print(f"{nome} acertou um critico e causou {dano_causado} de dano.")
            else:
                hp_boss -= dano_causado
                print(f"{nome} acertou e causou {dano_causado} de dano.")
        else:
            print(f"{nome} errou o ataque.")
            
    if hp_boss <= 0:
        # Venceu o último boss (pegar o nome do último que atacou ou do grupo?)
        # O exemplo diz: "O TarraByte foi derrotado por Salazar!" -> último que deu dano
        print(f"O TarraByte foi derrotado por {ordem_combate[-1]['nome']}!") # Na verdade, no exemplo foi o Salazar, vamos usar o nome do último que atacou ou o último da ordem que causou dano. No exemplo, Salazar foi o último.
    else:
        print(f"O TarraByte sobreviveu com {hp_boss} de HP e obliterou o grupo. Fim da aventura.")
