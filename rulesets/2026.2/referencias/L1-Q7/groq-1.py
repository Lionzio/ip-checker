# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-20b, 17/10/2026.
# Só a partir do enunciado da L1-Q7, sem nenhum código de aluno. Revise antes do merge.
import sys

def main():
    lines = [line.rstrip('\n') for line in sys.stdin]
    if not lines:
        return

    # Initial message
    print("Depois que a Série A e a Libertadores ficaram só no sonho do Santa, Byte pendura a chuteira de ídolo tricolor e parte pro interior: começa a Excursão Interiorana em busca do time da sua vida!")

    counted_visits = 0
    gostou_count = 0
    nao_gostou_count = 0
    catende_flag = False
    palmares_flag = False

    club_keywords = {
        "carcará": "Carcará no peito! Essa é terra de Salgueiro, o primeiro clube do interior a ser campeão pernambucano, Byte sente o chamado do Sertão!",
        "patativa": "Show da Patativa! Caruaru e o Central esperam Byte de braços abertos, direto da maior feira a céu aberto do mundo!",
        "azulão": "Ar puro de serra! O Azulão de Bonito, sensação recente do Pernambucano, pode ser o novo lar de Byte!",
        "fruticultura": "Margens do Velho Chico! Petrolina, a maior cidade do interior, com direito a manga, uva e muita irrigação, chama Byte pro time!",
        "pássaro preto": "Pertinho de casa! O Pássaro Preto, orgulhosamente um dos times mais folclóricos do planeta, também está de olho em Byte!"
    }

    for i in range(0, len(lines), 2):
        feature = lines[i]
        verdict = lines[i+1].strip()
        lower_feat = feature.lower()

        # Check special cities
        if "catende" in lower_feat:
            catende_flag = True
            print("Catende!!! Aqui já rodou a maior usina de açúcar e álcool da América Latina, Byte sente o orgulho no ar.")
        elif "palmares" in lower_feat:
            palmares_flag = True
            print("Palmares, a Terra dos Poetas! Berço de nomes como Ascenso Ferreira, aqui até o futebol merece um verso.")
        else:
            # Check clubs
            matched = False
            for kw, msg in club_keywords.items():
                if kw in lower_feat:
                    print(msg)
                    counted_visits += 1
                    matched = True
                    break
            # If no match, nothing before verdict

        # Verdict
        if verdict == "GOSTOU":
            print("Aquele cheirinho de interior fisgou o faro do Byte! Visita gostosa, mas ele quer conhecer mais um pouco antes de assinar.")
            gostou_count += 1
        else:
            print("Byte torceu o focinho dessa vez... não rolou clima pra ficar por aqui.")
            nao_gostou_count += 1

        # After second visit, check for Catende and Palmares
        if i == 2 and catende_flag and palmares_flag:
            print("Catende e Palmares na excursão? Aí sim Byte tá garimpando ouro puro da Zona da Mata Sul! Pena que acabou por aqui.")

    # Report
    print()
    print("RELATÓRIO DA EXCURSÃO SERTANEJA DO BYTE:")
    print(f"- Visitas que contaram: {counted_visits}")
    print(f"- Gostou: {gostou_count}")
    print(f"- Não gostou: {nao_gostou_count}")
    print()
    print("E assim termina a Excursão Interiorana de Byte em Pernambuco. Anotar tudo isso na unha, sem laço nem lista, dá um trabalhão! Nas próximas férias, Byte espera que a molecada já saiba de laços, listas e funções pra dar conta do recado com estilo :)")

if __name__ == "__main__":
    main()
