# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-120b, 17/10/2026.
# Só a partir do enunciado da L3-Q1, sem nenhum código de aluno. Revise antes do merge.
def main():
    sales = {
        "Dwight": [],
        "Jim": [],
        "Stanley": [],
        "Phillips": [],
        "Michael": []
    }
    known = {"Dwight", "Jim", "Stanley", "Phillips", "Michael"}

    while True:
        try:
            seller = input().strip()
        except EOFError:
            break
        if seller.lower() == "fim":
            break
        try:
            company = input().strip()
        except EOFError:
            break

        target = seller if seller in known else "Michael"
        sales[target].append(company)

    # Output
    if sales["Dwight"]:
        print(f"Dwight : {sales['Dwight']}")
    else:
        print("Dwight fez zero vendas hoje. Mais sorte amanhã!")

    if sales["Jim"]:
        print(f"Jim : {sales['Jim']}")
    else:
        print("Jim passou o dia fazendo pegadinhas e não concluiu nenhuma venda!")

    if sales["Stanley"]:
        print(f"Stanley : {sales['Stanley']}")
    else:
        print("Stanley acabou dormindo em serviço, amanhã ele estará mais descansado!")

    if sales["Phillips"]:
        print(f"Phillips : {sales['Phillips']}")
    else:
        print("Phillips se distraiu e acabou não fazendo vendas hoje!")

    if sales["Michael"]:
        print("Michael realizou vendas hoje!")
        print(f"Michael : {sales['Michael']}")
    else:
        print("Michael não trabalhou como vendedor hoje, apenas foi um bom chefe.")

if __name__ == "__main__":
    main()
