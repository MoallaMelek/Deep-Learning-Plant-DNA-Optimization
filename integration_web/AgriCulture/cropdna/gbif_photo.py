"""
gbif_photo.py
-------------
Fetches plant photos from iNaturalist API (free, CC licensed).
Downloads photo locally for use in HTML reports.
"""

import requests
import os


def get_inaturalist_photo(
    species_name : str,
    save_path    : str = None,
) -> dict:
    """
    Fetch a CC-licensed photo from iNaturalist for a species.
    Downloads the photo locally if save_path is provided.
    Returns dict: {url, local_path, license, photographer, source}
    """
    try:
        resp = requests.get(
            'https://api.inaturalist.org/v1/taxa',
            params={
                'q'    : species_name,
                'rank' : 'species',
                'limit': 1,
            },
            timeout=10
        )
        resp.raise_for_status()
        data    = resp.json()
        results = data.get('results', [])

        if not results:
            return None

        taxon     = results[0]
        photo     = taxon.get('default_photo', {})
        photo_url = photo.get('medium_url', '')
        license   = photo.get('license_code', 'cc-by')
        attrib    = photo.get('attribution', 'iNaturalist')

        if not photo_url:
            return None

        # Download locally
        local_path = None
        if save_path:
            img_resp = requests.get(photo_url, timeout=15)
            if img_resp.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(img_resp.content)
                local_path = save_path

        return {
            'url'          : photo_url,
            'local_path'   : local_path,
            'license'      : license,
            'photographer' : attrib,
            'location'     : 'iNaturalist',
            'source'       : 'iNaturalist',
        }

    except Exception as e:
        print(f'  iNaturalist error: {e}')
        return None


def get_primary_photo(
    species_name : str,
    country      : str = 'TN',
    save_path    : str = 'wheat_photo.jpg',
) -> dict:
    """
    Get primary photo for a species.
    Downloads locally and returns metadata.
    """
    return get_inaturalist_photo(species_name, save_path=save_path)


if __name__ == '__main__':
    photo = get_primary_photo('Triticum aestivum')
    if photo:
        print(f"URL        : {photo['url']}")
        print(f"Local path : {photo['local_path']}")
        print(f"License    : {photo['license']}")
        print(f"Source     : {photo['source']}")
    else:
        print("No photo found")
