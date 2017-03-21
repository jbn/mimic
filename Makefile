dockerize:
	docker build -t mimic_server .

composed:
	docker-compose build
	docker-compose up

serve_local:
	python -m mimic.server --host 0.0.0.0 --port 8901

serve_on_docker:
	docker run --rm -it -p 8901:8901 mimic_server
