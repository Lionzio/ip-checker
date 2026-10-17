# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L4-Q3, sem nenhum código de aluno. Revise antes do merge.
def montar_baralho():
    cartas = []
    while True:
        entrada = input()
        if entrada == "FIM":
            break
        cartas.append(entrada)
    print(f"{len(cartas)} cartas foram adicionadas ao baralho")
    return cartas


def receber_itens_e_totens(totem_atual):
    itens = []
    while True:
        entrada = input()
        if entrada == "FIM":
            break
        if entrada.lower() == "totem":
            classe = input().strip()
            totem_atual = classe.capitalize()
            print(f"Totem ativo: {totem_atual}")
        else:
            if len(itens) < 3:
                itens.append(entrada)
            else:
                print("Inventario cheio")
    
    itens_str = ", ".join(itens)
    print(f"Itens no inventario: {itens_str}")
    return itens, totem_atual


def calcular_coeficiente(baralho, itens, totem):
    canideos = ["lobo", "coiote", "cachorro"]
    insetos = ["louva-a-deus", "abelha", "formiga"]
    aves = ["corvo", "urubu", "pardal"]
    cervideos = ["antilocapra", "alce", "caribu"]
    repteis = ["rã", "tartaruga", "víbora"]
    cartas_raras = ["urayuli", "louva-a-deus rei", "ameba", "tubarão", "urso"]
    
    total = 0
    
    for carta in baralho:
        nome_l = carta.lower()
        if "pele" in nome_l:
            continue
        elif "filhote de" in nome_l or "ovo de" in nome_l:
            coef = 5
        elif nome_l in cartas_raras:
            coef = 20
        else:
            coef = 10
            
        if totem:
            t_lower = totem.lower()
            pertence = False
            if t_lower == "canideos" and any(c in nome_l for c in canideos):
                pertence = True
            elif t_lower == "insetos" and any(c in nome_l for c in insetos):
                pertence = True
            elif t_lower == "aves" and any(c in nome_l for c in aves):
                pertence = True
            elif t_lower == "cervideos" and any(c in nome_l for c in cervideos):
                pertence = True
            elif t_lower == "repteis" and any(c in nome_l for c in repteis):
                pertence = True
            
            if pertence:
                coef *= 2
                
        total += coef
        
    for item in itens:
        total += len(item.replace(" ", ""))
        
    return total


def simular_batalha(fase, coef_jogador, baralho):
    if fase == 1:
        print("Garimpeiro - É o Garimpeiro! OPA!")
        coef_chefe = 40
        coef_jogador = coef_jogador // 2
        if coef_jogador == coef_chefe:
            print("Leshy -  A fome se instala. Que lástima... chegou a hora da sua ruína.")
            return False
        elif coef_jogador > coef_chefe:
            print("Garimpeiro - Oxe!")
            return True
        else:
            print("Garimpeiro - Mais ouro pra mim!")
            return False
            
    elif fase == 2:
        print("Pescador - Eu sou o Pescador. Quer pescar?")
        coef_chefe = 90
        coef_jogador += coef_jogador // len(baralho) if baralho else 0
        if coef_jogador == coef_chefe:
            print("Leshy -  A fome se instala. Que lástima... chegou a hora da sua ruína.")
            return False
        elif coef_jogador > coef_chefe:
            print("Pescador - Vai pescar...")
            return True
        else:
            print("Pescador - Hum. Vai pescar.")
            return False
            
    elif fase == 3:
        print("Comerciante - Vamos negociar.")
        coef_chefe = 160
        peles = sum(1 for c in baralho if "pele" in c.lower())
        coef_chefe -= 10 * peles
        coef_jogador += 10 * peles
        if coef_jogador == coef_chefe:
            print("Leshy -  A fome se instala. Que lástima... chegou a hora da sua ruína.")
            return False
        elif coef_jogador > coef_chefe:
            print("Comerciante - Hmm... muito bem.")
            return True
        else:
            print("Comerciante - Você vai virar uma pele deslumbrante.")
            return False


def main():
    print("Leshy - Outro desafiante. Já faz tanto tempo...")
    
    totem_ativo = None
    baralho_total = []
    
    # Fase 1
    print("Leshy - O sol banha os abetos sonolentos, você adentrou o... matagal.")
    b1 = montar_baralho()
    baralho_total.extend(b1)
    itens1, totem_ativo = receber_itens_e_totens(totem_ativo)
    coef1 = calcular_coeficiente(baralho_total, itens1, totem_ativo)
    venceu1 = simular_batalha(1, coef1, baralho_total)
    if not venceu1:
        return
        
    # Fase 2
    print("Leshy - O ar úmido é tomado pelo cheiro fétido de mofo e morte, você caminha cautelosamente até entrar na... charneca.")
    b2 = montar_baralho()
    baralho_total.extend(b2)
    itens2, totem_ativo = receber_itens_e_totens(totem_ativo)
    coef2 = calcular_coeficiente(baralho_total, itens2, totem_ativo)
    venceu2 = simular_batalha(2, coef2, baralho_total)
    if not venceu2:
        return
        
    # Fase 3
    print("Leshy - O alívio do ar fresco logo dá lugar a um arrepio álgido. Você escala até a... linha de neve.")
    b3 = montar_baralho()
    baralho_total.extend(b3)
    itens3, totem_ativo = receber_itens_e_totens(totem_ativo)
    coef3 = calcular_coeficiente(baralho_total, itens3, totem_ativo)
    venceu3 = simular_batalha(3, coef3, baralho_total)
    if not venceu3:
        return
        
    print("Leshy - A luz cálida da cabana atravessa o denso nevoeiro... seus infortúnios acabam aqui.")


if __name__ == "__main__":
    main()
