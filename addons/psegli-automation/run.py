#!/usr/bin/env python3
"""PSEG New Jersey Automation Addon - FastAPI Server"""

import asyncio
import logging
import os
from typing import Dict, Optional

# Set HEADED=1 to run browser in headed mode (visible) for local MFA debugging
HEADED = os.environ.get("HEADED", "").lower() in ("1", "true", "yes")
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from auto_login import get_fresh_cookies, PSEGAutoLogin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PSEG New Jersey Automation", version="1.0.0")

if HEADED:
    logger.info("HEADED mode enabled - browser window will be visible for MFA debugging")

# Store in-progress MFA session (single session at a time)
_mfa_session: Optional[PSEGAutoLogin] = None

class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_code: Optional[str] = None  # If provided, used when MFA challenge appears
    mfa_method: Optional[str] = "sms"  # "email" or "sms" - which method to use for code delivery

class MfaRequest(BaseModel):
    code: str

class LoginResponse(BaseModel):
    success: bool
    cookies: Optional[str] = None
    error: Optional[str] = None
    mfa_required: Optional[bool] = None  # True when MFA needed - call POST /login/mfa with code

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "psegli-automation"}

@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login to PSEG and return cookies. If MFA is required, returns mfa_required=true - then POST to /login/mfa with the code."""
    global _mfa_session
    try:
        logger.info(f"Login attempt for user: {request.username}")
        
        # Clear any stale MFA session
        if _mfa_session:
            try:
                await _mfa_session.cleanup()
            except Exception:
                pass
            _mfa_session = None
        
        # Use direct PSEGAutoLogin to support two-phase MFA flow
        cookie_getter = PSEGAutoLogin(
            email=request.username,
            password=request.password,
            mfa_code=request.mfa_code,
            mfa_method=request.mfa_method or "sms",
            headless=not HEADED,
        )
        result = await cookie_getter.get_cookies()
        
        if result == "MFA_REQUIRED":
            _mfa_session = cookie_getter
            logger.info("MFA required - waiting for code via POST /login/mfa")
            return LoginResponse(
                success=False,
                mfa_required=True,
                error="PSEG requires multi-factor authentication. Check your email or phone for the verification code, then POST to /login/mfa with the code."
            )
        
        if result:
            logger.info("Login successful, cookies obtained")
            return LoginResponse(success=True, cookies=result)
        else:
            logger.warning("Login failed, no cookies returned")
            return LoginResponse(success=False, error="Login failed")
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return LoginResponse(success=False, error=str(e))

@app.post("/login/mfa", response_model=LoginResponse)
async def login_mfa(request: MfaRequest):
    """Complete login after MFA - provide the verification code from your email or SMS."""
    global _mfa_session
    if not _mfa_session:
        return LoginResponse(
            success=False,
            error="No MFA session in progress. Call POST /login first, then provide the code from your email or phone here."
        )
    try:
        logger.info("Completing MFA with provided code")
        cookies = await _mfa_session.continue_after_mfa(request.code)
        await _mfa_session.cleanup()
        _mfa_session = None
        
        if cookies:
            logger.info("MFA successful, cookies obtained")
            return LoginResponse(success=True, cookies=cookies)
        else:
            return LoginResponse(success=False, error="MFA verification failed - code may be invalid or expired")
    except Exception as e:
        logger.error(f"MFA error: {e}")
        if _mfa_session:
            try:
                await _mfa_session.cleanup()
            except Exception:
                pass
            _mfa_session = None
        return LoginResponse(success=False, error=str(e))

@app.post("/login-form", response_model=LoginResponse)
async def login_form(
    username: str = Form(...),
    password: str = Form(...),
    mfa_code: Optional[str] = Form(None),
    mfa_method: Optional[str] = Form("sms"),
):
    """Login endpoint that accepts form data."""
    return await login(LoginRequest(username=username, password=password, mfa_code=mfa_code, mfa_method=mfa_method))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
