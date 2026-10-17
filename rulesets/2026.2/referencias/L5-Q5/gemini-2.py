# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L5-Q5, sem nenhum código de aluno. Revise antes do merge.
INVENTÁRIO = {
    "nível": 0,
    'magias': [],
    'itens': {
        "pás": ["Pá do herói"],
    },
    'troféus': {
        'Capacete do Espectro': 0,
        'Capacete Gélido': 0
    }
}

ITENS = {
    "F": {"secao": "magias", "nome": "Varinha de Chamas", "mensagem": "O que é isso? Sinto um fogo emanando do fundo da minha alma…"},
    "V": {"secao": "magias", "nome": "Varinha de Gelo", "mensagem": "Uma magia nova é sempre bom!"},
    "P": {"secao": "pás", "nome": "Pá Espectral", "mensagem": "Uma pá transparente, que loucura!"},
    "p": {"secao": "pás", "nome": "Pá comum", "mensagem": "Mais uma para minha coleção."},
}

CHEFES = {
    "Specter Knight": {"capacete": "Capacete do Espectro", "nivel_minimo": 2},
    "Polar Knight": {"capacete": "Capacete Gélido", "nivel_minimo": 5},
}

DIRECOES = {"^": (-1, 0), "v": (1, 0), ">": (0, 1), "<": (0, -1)}

magias_catalogo = ["Pergaminho dos Elementos", "Varinha da Água", "Grimório de 4 folhas"]


def coletar_item(simbolo, inventario):
    info = ITENS[simbolo]
    secao = info["secao"]
    nome = info["nome"]
    print(info["mensagem"])
    if secao == "magias":
        inventario["magias"].append(nome)
    else:
        inventario["itens"][secao].append(nome)


def enfrentar(chefe, inventario, nivel, tem_requisito):
    dados = CHEFES[chefe]
    if nivel >= dados["nivel_minimo"] and tem_requisito:
        inventario["troféus"][dados["capacete"]] = 1
        return True
    return False


def mover_e_explorar(mapa, inventario):
    pos = (0, 0)
    while True:
        direcao = input()
        if direcao in DIRECOES:
            deslocamento = DIRECOES[direcao]
            nova_pos = (pos[0] + deslocamento[0], pos[1] + deslocamento[1])
            if 0 <= nova_pos[0] <= 4 and 0 <= nova_pos[1] <= 4:
                pos = nova_pos
                casa = mapa.get(pos, 0)
                if casa == "N":
                    inventario["nível"] += 1
                    mapa.pop(pos)
                elif casa in ITENS:
                    coletar_item(casa, inventario)
                    mapa.pop(pos)
                elif casa == "X":
                    break


def derrota():
    print("A jornada do herói chega a um triste fim…")
    print("Sua pá não foi capaz de cavar uma saída desse buraco de trevas em que estamos.")
    print("O que restou? Nada… brutal.")
    print()


def relatorio_final(inventario):
    print("======== RELATÓRIO FINAL ========")
    
    capacetes_coletados = []
    for cap, val in inventario["troféus"].items():
        if val == 1:
            capacetes_coletados.append(cap)
    if capacetes_coletados:
        print(f"CAPACETES: {', '.join(capacetes_coletados)}")
    else:
        print("CAPACETES: NENHUM")
        
    magias = inventario["magias"]
    if magias:
        print(f"MAGIAS: {', '.join(magias)}")
    else:
        print("MAGIAS: NENHUM")
        
    pas = inventario["itens"]["pás"]
    print(f"PÁS: {', '.join(pas)}")


def main():
    print("Shovel Knight, o lendário guerreiro, está de volta! Salvai-nos, ó herói da pá!")
    print()

    # Mercador
    resp = input()
    if resp == "sim":
        magia_pedida = input()
        if magia_pedida in magias_catalogo:
            INVENTÁRIO["magias"].append(magia_pedida)

    # CEMITÉRIO DOS LICHS
    print("======== CEMITÉRIO DOS LICHS ========")
    print("Um antigo vilarejo tomado pelos mortos. Me pergunto se aquele cavaleiro fantasma se esconde por aqui…")
    print("Black Knight? O que fazes aqui?")

    tem_magia_mercador = len(INVENTÁRIO["magias"]) > 0
    if tem_magia_mercador:
        print("Isso era um desafio?")
        print()
    else:
        derrota()
        relatorio_final(INVENTÁRIO)
        return

    mapa_cemiterio = {
        (0, 2): "p",
        (1, 4): "P",
        (2, 1): "N",
        (2, 2): "N",
        (2, 3): "F",
        (3, 3): "N",
        (3, 4): "N",
        (4, 0): "p",
        (4, 1): "X",
    }

    mover_e_explorar(mapa_cemiterio, INVENTÁRIO)

    print("Está na hora de caçar fantasmas!")
    tem_requisito_specter = ("Pá Espectral" in INVENTÁRIO["itens"]["pás"])
    venceu_specter = enfrentar("Specter Knight", INVENTÁRIO, INVENTÁRIO["nível"], tem_requisito_specter)

    if not venceu_specter:
        derrota()
        relatorio_final(INVENTÁRIO)
        return
    else:
        print()

    # NAVIO ENCALHADO
    print("======== NAVIO ENCALHADO ========")
    print("Uma embarcação antiga do Rei liderada pelo meu antigo mentor, o que será que encontrarei?")
    print("Você de novo? E que neve toda é essa?")

    qtd_pas = len(INVENTÁRIO["itens"]["pás"])
    if qtd_pas >= 3:
        print("Engraçado tentar parar um mestre das pás com neve, você se superou dessa vez!")
        print()
    else:
        print("Que saco! Onde estão minhas outras pás?")
        INVENTÁRIO["nível"] -= 3
        if INVENTÁRIO["nível"] <= 0:
            derrota()
            relatorio_final(INVENTÁRIO)
            return
        print()

    mapa_navio = {
        (0, 4): "X",
        (1, 3): "N",
        (2, 1): "N",
        (2, 2): "N",
        (3, 3): "N",
        (4, 1): "V",
    }

    mover_e_explorar(mapa_navio, INVENTÁRIO)

    print("Polar Knight! O what você está fazendo aqui?" if False else "Polar Knight! O que você está fazendo aqui?")
    print("Como pode trair nosso juramento?")

    tem_requisito_polar = (len(INVENTÁRIO["magias"]) >= 2)
    venceu_polar = enfrentar("Polar Knight", INVENTÁRIO, INVENTÁRIO["nível"], tem_requisito_polar)

    if not venceu_polar:
        derrota()
        relatorio_final(INVENTÁRIO)
        return
    else:
        print()

    # TORRE DO DESTINO
    print("======== TORRE DO DESTINO ========")
    print("Finalmente, aqui de novo…")
    
    pas_antigas = list(INVENTÁRIO["itens"]["pás"])
    print(f"ANTES - pás: {pas_antigas}")
    
    INVENTÁRIO["itens"]["pás"] = ["coragem do cavaleiro"]
    print(f"DEPOIS - pás: {INVENTÁRIO['itens']['pás']}")
    
    print("Perdi minhas pás, mas não posso recuar, agora é tudo ou nada!")

    while True:
        encantamento = input()
        if encantamento == "Droga, não tenho mais nada de mana!":
            break
        
        palavras = encantamento.split()
        if "morte" in palavras:
            INVENTÁRIO["nível"] -= 2
            print("Não posso recuar de jeito nenhum! Irei superar meus limites aqui e agora!")
        elif "magia" in palavras or "feitiço" in palavras:
            INVENTÁRIO["nível"] -= 1
            print("Não posso recuar de jeito nenhum! Irei superar meus limites aqui e agora!")

    if INVENTÁRIO["nível"] > 0:
        print("Minha amada! Finalmente pude revê-la e livrá-la desta terrível maldição!")
        print("Vamos embora deste lugar amaldiçoado!")
        print()
    else:
        derrota()
        relatorio_final(INVENTÁRIO)
        return

    relatorio_final(INVENTÁRIO)


main()
