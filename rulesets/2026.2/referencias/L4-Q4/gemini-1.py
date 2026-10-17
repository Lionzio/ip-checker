# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L4-Q4, sem nenhum código de aluno. Revise antes do merge.
import math

def calcular_erros(mao):
    copia = ['x'] + list(mao)
    limite = len(copia) // 2
    erros = 0
    marcados = set()
    
    for i in range(1, limite + 1):
        val = copia[i]
        idx1 = 2 * i
        idx2 = 2 * i + 1
        
        if idx1 < len(copia):
            if val < copia[idx1]:
                marcados.add(idx1)
                erros += 1
        if idx2 < len(copia):
            if val < copia[idx2]:
                marcados.add(idx2)
                erros += 1
                
    filtrada = []
    for idx in range(1, len(copia)):
        if idx not in marcados:
            filtrada.append(copia[idx])
            
    return filtrada, erros

def calcular_base(erros):
    if erros == 0:
        return "Full House", 40, 4.0
    elif erros == 1:
        return "Três do mesmo", 30, 3.0
    elif erros == 2:
        return "Dois pares", 20, 2.0
    else:
        return "Carta Maior", 5, 1.0

def aplicar_curingas(curingas, chips_base, mult_base):
    chips = chips_base
    mult = mult_base
    
    # Processa Blueprint
    efetivos = []
    for i in range(len(curingas)):
        c = curingas[i]
        if c == "Blueprint":
            if i + 1 < len(curingas):
                efetivos.append(curingas[i + 1])
        else:
            efetivos.append(c)
            
    for c in efetivos:
        if c == "Joker":
            mult += 4
        elif c == "Space Joker":
            chips += 20
            mult += 1
        elif c == "Chicot":
            pass
            
    return chips, mult

def aplicar_arcanos(arcanos_ativos, mao_filtrada, mult_atual):
    nova_mao = list(mao_filtrada)
    mult = mult_atual
    
    usados_hierofante = False
    usados_justica = False
    usados_forca = False
    
    for arc in arcanos_ativos:
        if arc == "Hierofante" and not usados_hierofante:
            usados_hierofante = True
            for i in range(len(nova_mao)):
                if nova_mao[i] < 30:
                    nova_mao[i] *= 2
        elif arc == "Justiça" and not usados_justica:
            usados_justica = True
            for x in nova_mao:
                if x % 3 == 0:
                    mult *= 1.1
        elif arc == "Força" and not usados_forca:
            usados_forca = True
            for i in range(len(nova_mao)):
                raiz = int(math.isqrt(nova_mao[i]))
                if raiz * raiz == nova_mao[i]:
                    nova_mao[i] += 50
                    
    return nova_mao, mult

def calcular_pontuacao_final(mao_filtrada, chips_totais, mult_total):
    soma_mao = sum(mao_filtrada)
    chips_finais = chips_totais + soma_mao
    mult_arredondado = round(mult_total, 2)
    pontuacao = int(chips_finais * mult_arredondado)
    return pontuacao, chips_finais

def main():
    meta = int(input())
    inventario = eval(input())
    
    curingas = []
    arcanos = []
    
    tipos_curingas = {"Joker", "Space Joker", "Blueprint", "Chicot"}
    for item in inventario:
        if item in tipos_curingas:
            curingas.append(item)
        else:
            arcanos.append(item)
            
    print(f"Jimbo: Certo, você tem que conseguir {meta} chips. Boa sorte!")
    print(f"Curingas: {', '.join(curingas)}")
    print(f"Arcanos: {', '.join(arcanos)}")
    
    maos_jogadas = 0
    trocas_restantes = 4
    maos_restantes = 4
    pontos_acumulados = 0
    venceu = False
    jogada_vitoria = 0
    
    while maos_restantes > 0 and pontos_acumulados < meta:
        mao = eval(input())
        
        while True:
            acao = input()
            if acao == "Jogar":
                break
            elif acao == "Trocar":
                if trocas_restantes > 0:
                    trocas_restantes -= 1
                    mao = eval(input())
            elif acao == "Arcano":
                if len(arcanos) > 0:
                    usado = arcanos.pop(0)
                    if usado == "Tolo":
                        novo_arc = input()
                        arcanos.append(novo_arc)
                    print(f"Arcanos: {', '.join(arcanos)}")
                    
        maos_jogadas += 1
        maos_restantes -= 1
        
        filtrada, erros = calcular_erros(mao)
        
        # Chicot
        chicot_count = curingas.count("Chicot")
        erros_efetivos = max(0, erros - (chicot_count * 2))
        
        classificacao, chips_base, mult_base = calcular_base(erros_efetivos)
        chips_parciais, mult_parcial = aplicar_curingas(curingas, chips_base, mult_base)
        
        if len(arcanos) > 0:
            arcano_da_vez = arcanos.pop(0)
            if arcano_da_vez == "Tolo":
                novo_arc = input()
                arcanos.append(novo_arc)
                arcanos_rodada = []
            else:
                arcanos_rodada = [arcano_da_vez]
            
            filtrada_final, mult_final = aplicar_arcanos(arcanos_rodada, filtrada, mult_parcial)
        else:
            filtrada_final = filtrada
            mult_final = mult_parcial
            
        pontuacao_final, chips_totais = calcular_pontuacao_final(filtrada_final, chips_parciais, mult_final)
        
        print(f"Classificação da mão: {classificacao}")
        
        mult_str = f"{mult_final:.2f}".rstrip('0').rstrip('.') if '.' in f"{mult_final:.2f}" else f"{mult_final:.2f}"
        print(f"{chips_totais} chips x {mult_str} = {pontuacao_final}")
        
        pontos_acumulados += pontuacao_final
        print(f"Total de chips: {pontos_acumulados}")
        
        if pontos_acumulados >= meta and not venceu:
            venceu = True
            jogada_vitoria = maos_jogadas
            break
            
    if venceu:
        print("Jimbo: Impressionante, você bateu a aposta.")
        if jogada_vitoria == 1:
            print("Jimbo: Balatro Balatrez esta a jugar balatro")
        elif maos_restantes == 0 and maos_jogadas == 4:
            print("Jimbo: Por pouco você falha, calculou bem.")
        else:
            print("Jimbo: Ainda bem que não apostei contra você.")
    else:
        faltam = meta - pontos_acumulados
        print(f"Jimbo: Mais que flop! Faltou {faltam} chips.")

if __name__ == '__main__':
    main()
