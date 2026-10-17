# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L5-Q2, sem nenhum código de aluno. Revise antes do merge.
def main():
    herois = ["Vax", "Pike", "Grog", "Percy", "Scanlan", "Vex", "Keyleth"]
    
    # Dicionário principal com dicionário interno para cada herói
    # Cada herói armazenará um dicionário de {arma: poder} e uma lista de ordem para desempate
    vox = {h: {} for h in herois}
    ordem_armas = {h: [] for h in herois}

    while True:
        linha = input().strip()
        if linha == "FIM":
            break
        
        partes = [p.strip() for p in linha.split(",")]
        if len(partes) < 3:
            continue
        
        nome = partes[0]
        arma = partes[1]
        poder = int(partes[2])
        
        if nome in vox:
            # Se a arma é nova para o herói, guarda a ordem de inserção
            if arma not in vox[nome]:
                ordem_armas[nome].append(arma)
            vox[nome][arma] = poder
            
            # Checagens de falas específicas
            if nome == "Vex" and arma == "Fenthras":
                print("Um arco mágico, capaz de controlar todos os elementos? isso é perfeito para mim querido!")
            elif nome == "Grog" and arma == "Manoplas de Titanstone":
                print("Estou maior agora, e pronto para entrar em fúria!")
            elif nome == "Vax" and arma == "Adaga Mágica":
                print("Uma arma dada pela própria rainha dos corvos, agora apenas preciso saber se isso é uma dádiva ou uma maldição.")
            elif nome == "Scanlan" and arma == "Caça Mitos":
                print("A espada lendária capaz de matar todos os Dragões... nas mãos do Scanlan?!")
            elif nome == "Keyleth" and arma == "Pináculo da Confluência":
                print("Com isso e meu aramenté completo, a natureza inteira estará sobre meu controle.")
            elif nome == "Percy" and arma == "The List":
                print("Não, ele novamente não, Orthax já me dominou uma vez, não posso deixar isso acontecer de novo.")
            elif nome == "Pike" and arma == "Placa do Mártir":
                print("Everlight, espero que um dia você me perdoe, mas não vou mais depender de você.")

    # Relatório final
    for h in herois:
        armas_heroi = vox[h]
        if not armas_heroi:
            print(f"{h} não possui nenhuma arma.")
        else:
            # Encontrar a mais forte respeitando a ordem de entrada (primeira a atingir o max)
            maior_poder = -1
            melhor_arma = ""
            for arma in ordem_armas[h]:
                poder = armas_heroi[arma]
                if poder > maior_poder:
                    maior_poder = poder
                    melhor_arma = arma
            print(f"A arma mais forte de {h} é a {melhor_arma} com {maior_poder} Pontos de Poder.")

if __name__ == "__main__":
    main()
