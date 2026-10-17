# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L2-Q4, sem nenhum código de aluno. Revise antes do merge.
def main():
    total_rodadas = int(input())
    recorde = int(input())

    print("Tigresa: Duvido você bater o recorde, Po!")
    print("Po: Prepare-se para ver o Dragão Guerreiro em ação!")

    total_geral = 0
    bater_por_extrapolacao = False
    total_ultima_rodada_extrapolacao = 0
    venceu_por_extrapolacao = False

    rodada_parou = total_rodadas + 1

    for r in range(1, total_rodadas + 1):
        if bater_por_extrapolacao:
            # Consome as entradas restantes caso o loop continue conceitualmente, mas aqui lemos normalmente
            bandejas = int(input())
            for _ in range(bandejas):
                int(input())
            continue

        bandejas = int(input())
        total_rodada = 0
        quebrou_na_rodada = False

        for _ in range(bandejas):
            bolinhos = int(input())
            total_rodada += bolinhos
            total_geral += bolinhos
            if total_geral > recorde and not quebrou_na_rodada:
                quebrou_na_rodada = True
                venceu_por_extrapolacao = True
                total_ultima_rodada_extrapolacao = total_rodada
                bater_por_extrapolacao = True

        if quebrou_na_rodada:
            print()
            print("Tigresa: Mas como?!")
            print("Po: UHUL! CONHEÇA A FORÇA DO DRAGÂO GUERREIRO!!")
            print(f"Rodada {r}: Po comeu {total_rodada} bolinhos.")
            rodada_parou = r
            break
        else:
            print()
            if total_rodada >= 10:
                print("Po: Delícia! Mais uma rodada finalizada!")
            else:
                print("Po: Ainda tenho espaço para mais!")
            print(f"Rodada {r}: Po comeu {total_rodada} bolinhos.")

    # Se não interrompeu por extrapolação, lê eventuais rodadas restantes se houver lógica redundante
    # Mas o loop já vai até total_rodadas.

    print()
    if venceu_por_extrapolacao:
        print("Po: Ei! Eu ainda não terminei!")
        print("Tigresa: Acho que não vou mais subestimar sua fome.")
        print(f"Que loucura! Po venceu a aposta comendo um total de {total_ultima_rodada_extrapolacao} bolinhos em uma só rodada!")
    elif total_geral > recorde:
        print("Po: Eu sabia que conseguiria! O recorde e meu!")
        print("Tigresa: Inacreditável... Você realmente venceu a aposta.")
        print(f"Po venceu a aposta! Ele comeu um total de {total_geral} bolinhos e superou o recorde de {recorde}!")
    elif total_geral == recorde:
        print("Po: Empatamos! Cheguei exatamente no recorde!")
        print("Tigresa: Impressionante, mas empatar não basta para vencer a aposta. Venha lavar a louça!")
        print(f"Houve um empate! Po comeu exatamente {total_geral} bolinhos e igualou o recorde de {recorde}.")
    else:
        print("Tigresa: Eu avisei, Po! A louça do palácio te espera.")
        print("Po: Ah não... Minhas mãos vão ficar enrugadas...")
        print(f"Tigresa venceu a aposta! Po comeu apenas {total_geral} bolinhos e não alcançou o recorde de {recorde}.")

if __name__ == "__main__":
    main()
