from fastapi import APIRouter, HTTPException, Query, Path
from domain.models import MatchDayFinancialReport
from parsers.factory import ExtractorFactory
from typing import Dict, Any
from services.cbf_scraper import CBFScraperService

router = APIRouter()

@router.get("/extract/team/{team_name}", response_model=Dict[str, Any])
def extract_team_reports(
    team_name: str = Path(..., description="The name of the club (e.g., 'Náutico')"),
    federation: str = Query("CBF", description="The origin federation of the PDF")
):
    """
    Automated endpoint: Searches across all divisions for the team, scrapes their 
    match history, downloads all borderôs in-memory, and extracts the OFC financial data.
    """

    scraper = CBFScraperService()

    try:
        extractor = ExtractorFactory.get_extractor(federation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        pdf_files_data = scraper.fetch_pdf_bytes_by_team(team_name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scraping failed: {str(e)}")

    if not pdf_files_data:
        raise HTTPException(status_code=404, detail=f"No financial reports found for team: {team_name}")

    successful_reports = []
    failed_reports = []
    
    for pdf_data in pdf_files_data:
        pdf_bytes = pdf_data["bytes"]
        pdf_url = pdf_data["url"]
        
        try:
            report = extractor.extract(pdf_bytes)
            report_dict = report.model_dump()
            report_dict["source_url"] = pdf_url
            successful_reports.append(report_dict)
        except ValueError as val_err:
            failed_reports.append({"url": pdf_url, "error_type": "Validation Error", "details": str(val_err)})
        except Exception as e:
            failed_reports.append({"url": pdf_url, "error_type": "Extraction Error", "details": str(e)})

    return {
        "status": "completed",
        "team_requested": team_name,
        "total_processed": len(pdf_files_data),
        "successful_extractions": len(successful_reports),
        "failed_extractions": len(failed_reports),
        "data": successful_reports,
        "errors": failed_reports
    }

@router.get("/teams", response_model=Dict[str, Any])
def list_teams_by_competition(
    competition: str = Query(..., description="The competition to list teams from (e.g., 'serie-a', 'serie-b', 'serie-c', 'serie-d')")
):
    """
    Lists all teams for a given competition.
    """
    if competition not in CBFScraperService.COMPETITIONS:
        raise HTTPException(status_code=400, detail=f"Invalid competition. Valid options are: {list(CBFScraperService.COMPETITIONS.keys())}")

    try:
        url = CBFScraperService.COMPETITIONS[competition]
        
        scraper = CBFScraperService()
        teams_data = scraper.find_teams(url)
        return {
            "competition": competition,
            "teams": teams_data
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch teams: {str(e)}")