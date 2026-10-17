# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-120b, 17/10/2026.
# Só a partir do enunciado da L3-Q1, sem nenhum código de aluno. Revise antes do merge.
def main():
    import sys

    vendedores = {
        "Dwight": [],
        "Jim": [],
        "Stanley": [],
        "Phillips": [],
        "Michael": []
    }

    it = iter(sys.stdin.read().splitlines())
    for linha in it:
        nome = linha.strip()
        if nome.lower() == "fim":
            break
        # próxima linha contém a empresa
        try:
            empresa = next(it).strip()
        except StopIteration:
            break  # entrada incompleta, encerra

        if nome in ("Dwight", "Jim", "Stanley", "Phillips"):
            vendedores[nome].append(empresa)
        else:
            # qualquer outro nome, inclusive "Michael", vai para Michael
            vendedores["Michael"].append(empresa)

    # Saídas na ordem requerida
    if vendedores["Dwight"]:
        print(f"Dwight : {vendedores['Dwight']}")
    else:
        print("Dwight fez zero vendas hoje. Mais sorte amanhã!")

    if vendedores["Jim"]:
        print(f"Jim : {vendedores['Jim']}")
    else:
        print("Jim passou o dia fazendo pegadinhas e não concluiu nenhuma venda!")

    if vendedores["Stanley"]:
        print(f"Stanley : {vendedores['Stanley']}")
    else:
        print("Stanley acabou dormindo em serviço, amanhã ele estará mais descansado!")

    if vendedores["Phillips"]:
        print(f"Phillips : {vendedores['Phillips']}")
    else:
        print("Phillips se distraiu e acabou não fazendo vendas hoje!")

    if vendedores["Michael"]:
        print("Michael realizou vendas hoje!")
        print(f"Michael : {vendedores['Michael']}")
    else:
        print("Michael não trabalhou como vendedor hoje, apenas foi um bom chefe.")


if __name__ == "__main__":
    main()
