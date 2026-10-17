# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-120b, 17/10/2026.
# Só a partir do enunciado da L1-Q3, sem nenhum código de aluno. Revise antes do merge.
def main():
    destino = input().strip()
    carisma = int(input())
    interesse_futebol = int(input())
    interesse_tenis = int(input())

    if destino == "Tsinghua":
        if carisma >= 90:
            if interesse_futebol > interesse_tenis:
                msg = "Todos os torcedores do Santa Cruz passam a ter acesso ao intercâmbio para a Tsinghua University."
            else:
                msg = "Os chineses gostam do Santa Cruz, mas preferem tênis de mesa e solicitam a criação do Santa Cruz Tênis de Mesa China."
        else:
            msg = "Byte consegue fazer amigos na universidade, mas a paixão pelo Santa Cruz fica para a próxima."
    elif destino == "Shenzhen":
        if interesse_futebol >= 80:
            if carisma == 100:
                msg = "Todos os chineses passam a torcer para o Santa Cruz."
            else:
                msg = "O Santa Cruz ganha um patrocínio de uma gigante de tecnologia de Shenzhen!"
        else:
            msg = "Byte falha em converter os chineses ao Santa Cruz, mas aproveita a viagem visitando Shenzhen."
    else:
        msg = "Passaporte invalido. Byte deve retornar a Recife."

    print(msg)


if __name__ == "__main__":
    main()
