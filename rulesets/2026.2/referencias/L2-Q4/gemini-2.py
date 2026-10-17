# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L2-Q4, sem nenhum código de aluno. Revise antes do merge.
def main():
    num_rodadas = int(input())
    recorde = int(input())

    print("Tigresa: Duvido você bater o recorde, Po!")
    print("Po: Prepare-se para ver o Dragão Guerreiro em ação!")

    total_geral = 0
    venceu_por_extrapolacao = False
    total_extrapolacao = 0
    bateu_recorde_geral = False

    rodadas_executadas = 0

    for r in range(1, num_rodadas + 1):
        if venceu_por_extrapolacao:
            # Consome as entradas restantes das rodadas que não ocorrerão
            num_bandejas = int(input())
            for _ in range(num_bandejas):
                input()
            continue

        rodadas_executadas = r
        num_bandejas = int(input())
        bolinhos_rodada = 0
        quebrou_nesta_rodada = False

        for _ in range(num_bandejas):
            b = int(input())
            bolinhos_rodada += b
            total_geral += b
            if total_geral > recorde and not venceu_por_extrapolacao:
                venceu_por_extrapolacao = True
                total_extrapolacao = bolinhos_rodada
                quebrou_nesta_rodada = True

        if quebrou_nesta_rodada:
            print()
            print("Tigresa: Mas como?!")
            print("Po: UHUL! CONHEÇA A FORÇA DO DRAGÂO GUERREIRO!!")
            print(f"Rodada {r}: Po comeu {bolinhos_rodada} bolinhos.")
            break
        else:
            print()
            if bolinhos_rodada >= 10:
                print("Po: Delícia! Mais uma rodada finalizada!")
            else:
                print("Po: Ainda tenho espaço para mais!")
            print(f"Rodada {r}: Po comeu {bolinhos_rodada} bolinhos.")

    if venceu_por_extrapolacao:
        print()
        print("Po: Ei! Eu ainda não terminei!")
        print("Tigresa: Acho que não vou mais subestimar sua fome.")
        print(f"Que loucura! Po venceu a aposta comendo um total de {total_extrapolacao} bolinhos em uma só rodada!")
    else:
        if total_geral > recorde:
            print()
            print("Po: Eu sabia que conseguiria! O recorde e meu!")
            print("Tigresa: Inacreditável... Você realmente venceu a aposta.")
            print(f"Po venceu a aposta! Ele comeu um total de {total_geral} bolinhos e superou o recorde de {recorde}!")
        elif total_geral == recorde:
            print()
            print("Po: Empatamos! Cheguei exatamente no recorde!")
            print("Tigresa: Impressionante, mas empatar não basta para vencer a aposta. Venha lavar a louça!")
            print(f"Houve um empate! Po comeu exatamente {total_geral} bolinhos e igualou o recorde de {recorde}.")
        else:
            print()
            print("Tigresa: Eu avisei, Po! A louça do palácio te espera.")
            print("Po: Ah não... Minhas mãos vão ficar enrugadas...")
            print(f"Tigresa venceu a aposta! Po comeu apenas {total_geral} bolinhos e não alcançou o recorde de {recorde}.")

if __name__ == "__main__":
    main()
