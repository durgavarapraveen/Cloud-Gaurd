from fastapi import FastAPI
from api.aws_routes import router as aws_router
from api.aws_policy_loader import router as aws_policy_router
from api.azure_policy_loader import router as azure_policy_router
from api.aws_checker_routes import router as aws_checker_router
from api.aws_scanner_route import router as aws_scanner_router
from api.yaml import router as yaml_router


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():

    return {"message": "Welcome to CloudGuard API!"}

app.include_router(aws_router)
app.include_router(aws_policy_router)
app.include_router(azure_policy_router)
app.include_router(aws_checker_router)
app.include_router(aws_scanner_router)
app.include_router(yaml_router)