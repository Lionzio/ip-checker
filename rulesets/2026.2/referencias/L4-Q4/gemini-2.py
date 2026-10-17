# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L4-Q4, sem nenhum código de aluno. Revise antes do merge.
import math

def calcular_base(erros):
    if erros == 0:
        return 40, 4
    elif erros == 1:
        return 30, 3
    elif erros == 2:
        return 20, 2
    else:
        return 5, 1

def aplicar_curingas(curingas, chips_base, mult_base):
    chips = chips_base
    mult = mult_base
    i = 0
    while i < len(curingas):
        c = curingas[i]
        if c == 'Joker':
            mult += 4
        elif c == 'Space Joker':
            chips += 20
            mult += 1
        elif c == 'Blueprint':
            if i + 1 < len(curingas):
                prox = curingas[i + 1]
                if prox == 'Joker':
                    mult += 4
                elif prox == 'Space Joker':
                    chips += 20
                    mult += 1
                elif prox == 'Chicot':
                    pass
        i += 1
    return chips, mult

def aplicar_arcanos(arcanos_ativos, mao_filtrada, mult):
    nova_mao = list(mao_filtrada)
    novo_mult = mult
    hierofante_usado = False
    justica_usado = False
    forca_usado = False

    for arc in arcanos_ativos:
        if arc == 'Hierofante' and not hierofante_usado:
            hierofante_usado = True
            for i in range(len(nova_mao)):
                if nova_mao[i] < 30:
                    nova_mao[i] *= 2
        elif arc == 'Justiça' and not justica_usado:
            justica_usado = True
            for val in nova_mao:
                if val % 3 == 0:
                    novo_mult *= 1.1
        elif arc == 'Força' and not forca_usado:
            forca_usado = True
            for i in range(len(nova_mao)):
                raiz = int(math.isqrt(nova_mao[i]))
                if raiz * raiz == nova_mao[i]:
                    nova_mao[i] += 50
    return nova_mao, novo_mult

def calcular_pontuacao_final(mao_filtrada, chips_totais, mult):
    soma_cartas = sum(mao_filtrada)
    chips_fin = chips_totais + soma_cartas
    pontuacao = int(chips_fin * round(mult, 2))
    return pontuacao, chips_fin

def processar_mao(mao):
    copia = ['x'] + list(mao)
    limite = len(copia) // 2
    marcados = set()
    erros = 0
    for i in range(1, limite + 1):
        val = copia[i]
        idx1 = 2 * i
        idx2 = 2 * i + 1
        if idx1 < len(copia):
            if val < copia[idx1]:
                if idx1 not in marcados:
                    marcados.add(idx1)
                    erros += 1
        if idx2 < len(copia):
            if val < copia[idx2]:
                if idx2 not in marcados:
                    marcados.add(idx2)
                    erros += 1
    filtrada = []
    for i in range(1, len(copia)):
        if i not in marcados:
            filtrada.append(copia[i])
    return filtrada, erros

def main():
    meta = int(input())
    inventario = eval(input())

    curingas = []
    arcanos = []
    for item in inventario:
        if item in ['Joker', 'Space Joker', 'Blueprint', 'Chicot']:
            curingas.append(item)
        else:
            arcanos.append(item)

    print(f"Jimbo: Certo, você tem que conseguir {meta} chips. Boa sorte!")
    print(f"Curingas: {', '.join(curingas)}")
    print(f"Arcanos: {', '.join(arcanos)}")

    pontos_acumulados = 0
    maos_jogadas = 0
    trocas_restantes = 4

    mao = eval(input())

    while maos_jogadas < 4 and pontos_acumulados < meta:
        acao = input().strip()
        while acao != "Jogar":
            if acao == "Trocar":
                if trocas_restantes > 0:
                    mao = eval(input())
                    trocas_restantes -= 1
                else:
                    input() # descarta a nova_mao se nao puder trocar
            elif acao == "Arcano":
                if len(arcanos) > 0:
                    usado = arcanos.pop(0)
                    if usado == 'Tolo':
                        novo_arcano = input().strip()
                        arcanos.append(novo_arcano)
                    print(f"Arcanos: {', '.join(arcanos)}")
            acao = input().strip()

        # Ação é "Jogar"
        maos_jogadas += 1
        filtrada, erros = processar_mao(mao)

        chicot_count = curingas.count('Chicot')
        erros_efetivos = max(0, erros - chicot_count * 2)

        if erros_efetivos == 0:
            classificacao = "Full House"
        elif erros_efetivos == 1:
            classificacao = "Três do mesmo"
        elif erros_efetivos == 2:
            classificacao = "Dois pares"
        else:
            classificacao = "Carta Maior"

        chips_b, mult_b = calcular_base(erros_efetivos)
        chips_c, mult_c = aplicar_curingas(curingas, chips_b, mult_b)
        
        # Arcanos aplicados ao jogar
        mao_final, mult_final = aplicar_arcanos(arcanos, filtrada, mult_c)
        
        pontuacao_final, chips_totais = calcular_pontuacao_final(mao_final, chips_c, mult_final)
        pontos_acumulados += pontuacao_final

        print(f"Classificação da mão: {classificacao}")
        print(f"{chips_totais} chips x {round(mult_final, 2)} = {pontuacao_final}")
        print(f"Total de chips: {pontos_acumulados}")

        if pontos_acumulados >= meta:
            break

        if maos_jogadas < 4:
            try:
                mao = eval(input())
            except EOFError:
                break

    if pontos_acumulados >= meta:
        print("Jimbo: Impressionante, você bateu a aposta.")
        if maos_jogadas == 1:
            print("Jimbo: Balatro Balatrez esta a jugar balatro")
        elif maos_jogadas == 4:
            print("Jimbo: Por pouco você falha, calculou bem.")
        else:
            print("Jimbo: Ainda bem que não apostei contra você.")
    else:
        faltam = meta - pontos_acumulados
        print(f"Jimbo: Mais que flop! Faltou {faltam} chips.")

if __name__ == '__main__':
    main()
