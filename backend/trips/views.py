from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import PlanRequestSerializer
from .services.http import ProviderError
from .services.planner import plan_trip
from .services.tomtom import geocode


def _provider_error(exc):
    return Response({"detail": exc.message}, status=exc.status)


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def geocode_view(request):
    q = request.query_params.get("q", "").strip()
    if len(q) < 3:
        return Response({"results": []})
    try:
        places = geocode(q[:200])
    except ProviderError as exc:
        return _provider_error(exc)
    return Response({"results": [{"lat": p.lat, "lon": p.lon, "label": p.label} for p in places]})


@api_view(["POST"])
def plan_view(request):
    ser = PlanRequestSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    try:
        result = plan_trip(**ser.validated_data)
    except ProviderError as exc:
        return _provider_error(exc)
    return Response(result)
