# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L5-Q2, sem nenhum código de aluno. Revise antes do merge.
def main():
    integrantes = ["Vax", "Pike", "Grog", "Percy", "Scanlan", "Vex", "Keyleth"]
    
    # Dicionário de dicionários para armazenar as armas de cada herói
    # Cada herói terá uma lista de tuplas (arma, poder) para preservar a ordem de entrada (desempate)
    armas_herois = {heroi: {} for heroi in integrantes}
    ordem_armas = {heroi: [] for heroi in integrantes}

    while True:
        linha = input().strip()
        if linha == "FIM" or not linha:
            break
        
        partes = [p.strip() for p in linha.split(",")]
        if len(partes) < 3:
            continue
            
        heroi = partes[0]
        arma = partes[1]
        poder = int(partes[2])

        # Verificações de falas específicas
        if heroi == "Vex" and arma == "Fenthras":
            print("Um arco mágico, capaz de controlar todos os elementos? isso é perfeito para mim querido!")
        elif heroi == "Grog" and arma == "Manoplas de Titanstone":
            print("Estou maior agora, e pronto para entrar em fúria!")
        elif heroi == "Vax" and arma == "Adaga Mágica":
            print("Uma arma dada pela própria rainha dos corvos, agora apenas preciso saber se isso é uma dádiva ou uma maldição.")
        elif heroi == "Scanlan" and arma == "Caça Mitos":
            print("A espada lendária capaz de matar todos os Dragões... nas mãos do Scanlan?!")
        elif heroi == "Keyleth" and arma == "Pináculo da Confluência":
            print("Com isso e meu aramenté completo, a natureza inteira estará sobre meu controle.")
        elif heroi == "Percy" and arma == "The List":
            print("Não, ele novamente não, Orthax já me dominou uma vez, não posso deixar isso acontecer de novo.")
        elif heroi == "Pike" and arma == "Placa do Mártir":
            print("Everlight, espero que um dia você me perdoe, mas não vou mais depender de você.")

        if heroi in armas_herois:
            # Armazenamos no dicionário interno
            armas_herois[heroi][arma] = poder
            # E mantemos a lista de inserção para garantir o critério de desempate (primeira inserida)
            # Caso a arma já exista, podemos atualizar ou apenas adicionar à ordem. 
            # O enunciado diz que a arma é adicionada. Se repetir, atualiza o poder.
            if arma not in ordem_armas[heroi]:
                ordem_armas[heroi].append(arma)

    # Relatório final
    for heroi in integrantes:
        dicionario_armas = armas_herois[heroi]
        if not dicionario_armas:
            print(f"{heroi} não possui nenhuma arma.")
        else:
            # Encontrar a mais forte respeitando a ordem de entrada
            maior_poder = -1
            melhor_arma = ""
            for arma in ordem_armas[heroi]:
                poder = dicionario_armas[arma]
                if poder > maior_poder:
                    maior_poder = poder
                    melhor_arma = arma
            
            print(f"A arma mais forte de {heroi} é a {melhor_arma} com {maior_poder} Pontos de Poder.")

if __name__ == "__main__":
    main()
