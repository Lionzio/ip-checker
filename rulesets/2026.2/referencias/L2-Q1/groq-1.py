# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-120b, 17/10/2026.
# Só a partir do enunciado da L2-Q1, sem nenhum código de aluno. Revise antes do merge.
def main():
    try:
        n = int(input())
    except EOFError:
        return

    seen = set()
    unique = []
    repetitions = 0

    for _ in range(n):
        vaga = input().strip()
        if vaga in seen:
            repetitions += 1
        else:
            seen.add(vaga)
            unique.append(vaga)

    print("Parabéns formandos! E agora iniciaremos sua carreira nas indústrias Honex.")
    print(" - ".join(unique))
    print(f"Quantidade de cargos repetidos: {repetitions}")

    if len(unique) > repetitions:
        print("Pelo menos Barry tem opções!")
    else:
        print("Mais do mesmo. Barry será apenas uma engrenagem na máquina de mel.")


if __name__ == "__main__":
    main()
