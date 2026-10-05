import argparse
import os


def main():
    p = argparse.ArgumentParser(prog="radar-concursos", description="Radar Concursos — monitor de concursos públicos")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect", help="roda a coleta das fontes agora")
    c.add_argument("--fonte", help="fontes separadas por vírgula: dou,queridodiario,fcc,ibfc,googlenews")

    s = sub.add_parser("serve", help="sobe a interface web")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--sem-agenda", action="store_true", help="não agenda coletas automáticas")

    st = sub.add_parser("stats", help="resumo do banco de dados")

    args = p.parse_args()

    if args.cmd == "serve" and args.sem_agenda:
        os.environ["CONCURSO_INTERVALO_HORAS"] = "0"

    from app import database
    database.init_db()

    if args.cmd == "collect":
        from app.ingest import rodar_coleta
        fontes = args.fonte.split(",") if args.fonte else None
        resumo = rodar_coleta(fontes)
        for fonte, info in resumo.items():
            if info.get("erro"):
                print(f"{fonte}: ERRO - {info['erro']}")
            else:
                print(f"{fonte}: {info['vistos']} vistos, {info['novos']} novos")
    elif args.cmd == "serve":
        import uvicorn
        from app.main import app
        print(f"Interface: http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    elif args.cmd == "stats":
        from app.database import conectar
        with conectar() as c:
            print("Concursos por status:")
            for status, n in c.execute("SELECT status, COUNT(*) FROM concursos GROUP BY status ORDER BY 2 DESC"):
                print(f"  {status}: {n}")
            total_ufs = c.execute("SELECT COUNT(DISTINCT uf) FROM concursos WHERE uf IS NOT NULL").fetchone()[0]
            total = c.execute("SELECT COUNT(*) FROM concursos").fetchone()[0]
            print(f"Total: {total} concursos, {total_ufs} estados")
            print("Últimas execuções:")
            for r in c.execute("SELECT fonte, fim, itens_vistos, itens_novos, erro FROM execucoes ORDER BY id DESC LIMIT 10"):
                estado = "ERRO" if r["erro"] else "ok"
                print(f"  {r['fonte']}: {r['fim']} ({r['itens_vistos']} vistos, {r['itens_novos']} novos) [{estado}]")


if __name__ == "__main__":
    main()
