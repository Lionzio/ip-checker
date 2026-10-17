# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-20b, 17/10/2026.
# Só a partir do enunciado da L1-Q7, sem nenhum código de aluno. Revise antes do merge.
import sys

def main():
    lines = [line.rstrip('\n') for line in sys.stdin]
    print("Depois que a Série A e a Libertadores ficaram só no sonho do Santa, Byte pendura a chuteira de ídolo tricolor e parte pro interior: começa a Excursão Interiorana em busca do time da sua vida!")
    
    catende_seen = False
    palmares_seen = False
    real_visits = 0
    liked = 0
    disliked = 0
    
    i = 0
    while i + 1 < len(lines):
        feature = lines[i]
        verdict = lines[i+1]
        i += 2
        
        if "Catende" in feature:
            print("Catende!!! Aqui já rodou a maior usina de açúcar e álcool da América Latina, Byte sente o orgulho no ar.")
            catende_seen = True
        elif "Palmares" in feature:
            print("Palmares, a Terra dos Poetas! Berço de nomes como Ascenso Ferreira, aqui até o futebol merece um verso.")
            palmares_seen = True
        else:
            real_visits += 1
            if "Carcará" in feature:
                print("Carcará no peito! Essa é terra de Salgueiro, o primeiro clube do interior a ser campeão pernambucano, Byte sente o chamado do Sertão!")
            elif "Patativa" in feature:
                print("Show da Patativa! Caruaru e o Central esperam Byte de braços abertos, direto da maior feira a céu aberto do mundo!")
            elif "Azulão" in feature:
                print("Ar puro de serra! O Azulão de Bonito, sensação recente do Pernambucano, pode ser o novo lar de Byte!")
            elif "fruticultura" in feature:
                print("Margens do Velho Chico! Petrolina, a maior cidade do interior, com direito a manga, uva e muita irrigação, chama Byte pro time!")
            elif "Pássaro Preto" in feature:
                print("Pertinho de casa! O Pássaro Preto, orgulhosamente um dos times mais folclóricos do planeta, também está de olho em Byte!")
        
        if verdict == "GOSTOU":
            print("Aquele cheirinho de interior fisgou o faro do Byte! Visita gostosa, mas ele quer conhecer mais um pouco antes de assinar.")
            liked += 1
        else:
            print("Byte torceu o focinho dessa vez... não rolou clima pra ficar por aqui.")
            disliked += 1
    
    if catende_seen and palmares_seen:
        print("Catende e Palmares na excursão? Aí sim Byte tá garimpando ouro puro da Zona da Mata Sul! Pena que acabou por aqui.")
    
    print()
    print("RELATÓRIO DA EXCURSÃO SERTANEJA DO BYTE:")
    print(f"- Visitas que contaram: {real_visits}")
    print(f"- Gostou: {liked}")
    print(f"- Não gostou: {disliked}")
    print()
    print("E assim termina a Excursão Interiorana de Byte em Pernambuco. Anotar tudo isso na unha, sem laço nem lista, dá um trabalhão! Nas próximas férias, Byte espera que a molecada já saiba de laços, listas e funções pra dar conta do recado com estilo :)")

if __name__ == "__main__":
    main()
