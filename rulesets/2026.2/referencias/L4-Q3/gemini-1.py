# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L4-Q3, sem nenhum código de aluno. Revise antes do merge.
def montar_baralho():
    cartas = []
    while True:
        c = input()
        if c == "FIM":
            break
        cartas.append(c)
    print(f"{len(cartas)} cartas foram adicionadas ao baralho")
    return cartas


def receber_itens_e_totens(totem_atual):
    itens = []
    while True:
        linha = input()
        if linha == "FIM":
            break
        if linha.lower() == "totem":
            classe = input()
            totem_atual = classe.lower()
            print(f"Totem ativo: {classe.capitalize()}")
        else:
            if len(itens) < 3:
                itens.append(linha)
            else:
                print("Inventario cheio")
    
    itens_str = ", ".join(itens)
    print(f"Itens no inventario: {itens_str}")
    return itens, totem_atual


def calcular_coeficiente(baralho, itens, totem_ativo):
    cartas_raras = ["urayuli", "louva-a-deus rei", "ameba", "tubarão", "urso"]
    canideos = ["lobo", "coiote", "cachorro"]
    insetos = ["louva-a-deus", "abelha", "formiga"]
    aves = ["corvo", "urubu", "pardal"]
    cervideos = ["antilocapra", "alce", "caribu"]
    repteis = ["rã", "tartaruga", "víbora"]

    total = 0
    for carta in baralho:
        c_lower = carta.lower()
        if "pele" in c_lower:
            coef = 0
        elif "filhote de" in c_lower or "ovo de" in c_lower:
            coef = 5
        elif c_lower in cartas_raras:
            coef = 20
        else:
            coef = 10

        if totem_ativo:
            pertence = False
            if totem_ativo == "canideos" and any(x in c_lower for x in canideos):
                pertence = True
            elif totem_ativo == "insetos" and any(x in c_lower for x in insetos):
                pertence = True
            elif totem_ativo == "aves" and any(x in c_lower for x in aves):
                pertence = True
            elif totem_ativo == "cervideos" and any(x in c_lower for x in cervideos):
                pertence = True
            elif totem_ativo == "repteis" and any(x in c_lower for x in repteis):
                pertence = True

            if pertence:
                coef *= 2

        total += coef

    for item in itens:
        total += len(item.replace(" ", ""))

    return total


def simular_batalha(fase, baralho, itens, totem_ativo):
    coef_jogador = calcular_coeficiente(baralho, itens, totem_ativo)
    peles_count = sum(1 for c in baralho if "pele" in c.lower())

    if fase == 1:
        print("Garimpeiro - É o Garimpeiro! OPA!")
        coef_jogador //= 2
        chef_coef = 40
        if coef_jogador == chef_coef:
            print("Leshy -  A fome se instala. Que lástima... chegou a hora da sua ruína.")
            return False
        elif coef_jogador > chef_coef:
            print("Garimpeiro - Oxe!")
            return True
        else:
            print("Garimpeiro - Mais ouro pra mim!")
            return False

    elif fase == 2:
        print("Pescador - Eu sou o Pescador. Quer pescar?")
        chef_coef = 90
        if coef_jogador == chef_coef:
            print("Leshy -  A fome se instala. Que lástima... chegou a hora da sua ruína.")
            return False
        elif coef_jogador > chef_coef:
            print("Pescador - Vai pescar...")
            return True
        else:
            print("Pescador - Hum. Vai pescar.")
            return False

    elif fase == 3:
        print("Comerciante - Vamos negociar.")
        chef_coef = 160 - (10 * peles_count)
        coef_jogador += 10 * peles_count
        if coef_jogador == chef_coef:
            print("Leshy -  A fome se instala. Que lástima... chegou a hora da sua ruína.")
            return False
        elif coef_jogador > chef_coef:
            print("Comerciante - Hmm... muito bem.")
            return True
        else:
            print("Comerciante - Você vai virar uma pele deslumbrante.")
            return False


def main():
    print("Leshy - Outro desafiante. Já faz tanto tempo...")
    baralho = []
    totem_ativo = None

    # Fase 1
    print("Leshy - O sol banha os abetos sonolentos, você adentrou o... matagal.")
    novas_cartas = montar_baralho()
    baralho.extend(novas_cartas)
    itens, totem_ativo = receber_itens_e_totens(totem_ativo)
    venceu = simular_batalha(1, baralho, itens, totem_ativo)
    if not venceu:
        return

    # Fase 2
    print("Leshy - O ar úmido é tomado pelo cheiro fétido de mofo e morte, você caminha cautelosamente até entrar na... charneca.")
    novas_cartas = montar_baralho()
    baralho.extend(novas_cartas)
    itens, totem_ativo = receber_itens_e_totens(totem_ativo)
    venceu = simular_batalha(2, baralho, itens, totem_ativo)
    if not venceu:
        return

    # Fase 3
    print("Leshy - O alívio do ar fresco logo dá lugar a um arrepio álgido. Você escala até a... linha de neve.")
    novas_cartas = montar_baralho()
    baralho.extend(novas_cartas)
    itens, totem_ativo = receber_itens_e_totens(totem_ativo)
    venceu = simular_batalha(3, baralho, itens, totem_ativo)
    if not venceu:
        return

    print("Leshy - A luz cálida da cabana atravessa o denso nevoeiro... seus infortúnios acabam aqui.")


if __name__ == "__main__":
    main()
