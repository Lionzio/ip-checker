# Solução gerada por IA (S42-04, ADR-08): groq, modelo openai/gpt-oss-20b, 17/10/2026.
# Só a partir do enunciado da L2-Q4, sem nenhum código de aluno. Revise antes do merge.
import sys

def main():
    data = list(map(int, sys.stdin.read().strip().split()))
    if not data:
        return
    it = iter(data)
    try:
        rounds = next(it)
        record = next(it)
    except StopIteration:
        return

    cumulative = 0
    record_break = False
    record_break_before_end = False
    record_break_round_total = 0

    out_lines = []
    out_lines.append("Tigresa: Duvido você bater o recorde, Po!")
    out_lines.append("Po: Prepare-se para ver o Dragão Guerreiro em ação!")
    out_lines.append("")  # blank line

    for r in range(1, rounds + 1):
        try:
            trays = next(it)
        except StopIteration:
            break
        round_total = 0
        for t in range(trays):
            try:
                bol = next(it)
            except StopIteration:
                bol = 0
            round_total += bol
            cumulative += bol
            if not record_break and cumulative > record:
                record_break = True
                if t < trays - 1:
                    record_break_before_end = True
        # Messages for the round
        if record_break_before_end:
            out_lines.append("Tigresa: Mas como?!")
            out_lines.append("Po: UHUL! CONHEÇA A FORÇA DO DRAGÂO GUERREIRO!!")
        else:
            if round_total >= 10:
                out_lines.append("Po: Delícia! Mais uma rodada finalizada!")
            else:
                out_lines.append("Po: Ainda tenho espaço para mais!")
        out_lines.append(f"Rodada {r}: Po comeu {round_total} bolinhos.")
        out_lines.append("")  # blank line after round
        if record_break:
            record_break_round_total = round_total
            break

    # Final block
    if record_break_before_end:
        out_lines.append("Po: Ei! Eu ainda não terminei!")
        out_lines.append("Tigresa: Acho que não vou mais subestimar sua fome.")
        out_lines.append(f"Que loucura! Po venceu a aposta comendo um total de {record_break_round_total} bolinhos em uma só rodada!")
    else:
        if cumulative > record:
            out_lines.append("Po: Eu sabia que conseguiria! O recorde e meu!")
            out_lines.append("Tigresa: Inacreditável... Você realmente venceu a aposta.")
            out_lines.append(f"Po venceu a aposta! Ele comeu um total de {cumulative} bolinhos e superou o recorde de {record}!")
        elif cumulative == record:
            out_lines.append("Po: Empatamos! Cheguei exatamente no recorde!")
            out_lines.append("Tigresa: Impressionante, mas empatar não basta para vencer a aposta. Venha lavar a louça!")
            out_lines.append(f"Houve um empate! Po comeu exatamente {cumulative} bolinhos e igualou o recorde de {record}.")
        else:
            out_lines.append("Tigresa: Eu avisei, Po! A louça do palácio te espera.")
            out_lines.append("Po: Ah não... Minhas mãos vão ficar enrugadas...")
            out_lines.append(f"Tigresa venceu a aposta! Po comeu apenas {cumulative} bolinhos e não alcançou o recorde de {record}.")

    sys.stdout.write("\n".join(out_lines))

if __name__ == "__main__":
    main()
