# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L3-Q1, sem nenhum código de aluno. Revise antes do merge.
def main():
    vendas = {
        "Dwight": [],
        "Jim": [],
        "Stanley": [],
        "Phillips": [],
        "Michael": []
    }

    while True:
        vendedor = input().strip()
        if vendedor.lower() == "fim":
            break
        empresa = input().strip()

        if vendedor in vendas:
            vendas[vendedor].append(empresa)
        else:
            vendas["Michael"].append(empresa)

    # 1. Dwight
    if vendas["Dwight"]:
        print(f"Dwight : {vendas['Dwight']}")
    else:
        print("Dwight fez zero vendas hoje. Mais sorte amanhã!")

    # 2. Jim
    if vendas["Jim"]:
        print(f"Jim : {vendas['Jim']}")
    else:
        print("Jim passou o dia fazendo pegadinhas e não concluiu nenhuma venda!")

    # 3. Stanley
    if vendas["Stanley"]:
        print(f"Stanley : {vendas['Stanley']}")
    else:
        print("Stanley acabou dormindo em serviço, amanhã ele estará mais descansado!")

    # 4. Phillips
    if vendas["Phillips"]:
        print(f"Phillips : {vendas['Phillips']}")
    else:
        print("Phillips se distraiu e acabou não fazendo vendas hoje!")

    # 5. Michael
    if vendas["Michael"]:
        print("Michael realizou vendas hoje!")
        print(f"Michael : {vendas['Michael']}")
    else:
        print("Michael não trabalhou como vendedor hoje, apenas foi um bom chefe.")

if __name__ == "__main__":
    main()
