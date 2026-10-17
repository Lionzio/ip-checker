# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L2-Q1, sem nenhum código de aluno. Revise antes do merge.
def main():
    n = int(input())
    
    vagas_unicas = []
    repeticoes = 0
    
    for _ in range(n):
        vaga = input()
        if vaga in vagas_unicas:
            repeticoes += 1
        else:
            vagas_unicas.append(vaga)
            
    print("Parabéns formandos! E agora iniciaremos sua carreira nas indústrias Honex.")
    print(" - ".join(vagas_unicas))
    print(f"Quantidade de cargos repetidos: {repeticoes}")
    
    if len(vagas_unicas) > repeticoes:
        print("Pelo menos Barry tem opções!")
    else:
        print("Mais do mesmo. Barry será apenas uma engrenagem na máquina de mel.")

if __name__ == "__main__":
    main()
