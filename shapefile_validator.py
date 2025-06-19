#!/usr/bin/env python3
"""
Fixed Shapefile Validation Tool

This version fixes inconsistent validation reporting and ensures
the validation results are properly accumulated and reported.

Requirements:
- Python 3.6+
- GDAL/OGR Python bindings
"""

import os
import sys
import zipfile
import tempfile
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional

try:
    from osgeo import ogr, osr
    from osgeo import gdal
    gdal.UseExceptions()
except ImportError:
    print("ERROR: GDAL/OGR Python bindings not found. Install with:")
    print("  pip install gdal")
    print("  or")
    print("  conda install gdal")
    sys.exit(1)

class ShapefileValidator:
    """Validates shapefiles according to specified criteria."""
    
    REQUIRED_EXTENSIONS = {'.shp', '.shx', '.dbf', '.prj'}
    OPTIONAL_EXTENSIONS = {'.cpg', '.sbn', '.sbx', '.fbn', '.fbx', '.ain', '.aih', '.ixs', '.mxs', '.atx', '.xml'}
    WGS84_EPSG = 4326
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.validation_details = []  # Track individual validation steps
        
    def validate_zip_archive(self, zip_path: str) -> Tuple[bool, List[str]]:
        """
        Validate a ZIP archive containing shapefile(s).
        
        Args:
            zip_path: Path to ZIP file
            
        Returns:
            Tuple of (is_valid, list_of_shapefiles_found)
        """
        # Clear previous results
        self.errors.clear()
        self.warnings.clear()
        self.validation_details.clear()
        
        if not os.path.exists(zip_path):
            self.errors.append(f"File not found: {zip_path}")
            return False, []
            
        if not zipfile.is_zipfile(zip_path):
            self.errors.append(f"File is not a valid ZIP archive: {zip_path}")
            return False, []
            
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                # Find potential shapefiles
                shapefiles = self._find_shapefiles_in_zip(file_list)
                
                if not shapefiles:
                    self.errors.append("No shapefiles found in ZIP archive")
                    return False, []
                
                # Track overall validation status
                all_shapefiles_valid = True
                
                # Validate each shapefile
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_ref.extractall(temp_dir)
                    
                    for shapefile_base in shapefiles:
                        shapefile_path = os.path.join(temp_dir, f"{shapefile_base}.shp")
                        
                        # Track per-shapefile validation
                        shapefile_valid = self._validate_individual_shapefile(shapefile_path, shapefile_base)
                        
                        if not shapefile_valid:
                            all_shapefiles_valid = False
                
                return all_shapefiles_valid, shapefiles
                
        except Exception as e:
            self.errors.append(f"Error processing ZIP file: {str(e)}")
            return False, []
    
    def _find_shapefiles_in_zip(self, file_list: List[str]) -> List[str]:
        """Find shapefile base names in ZIP file list."""
        # Get all .shp files and extract base names
        shp_files = [f for f in file_list if f.lower().endswith('.shp')]
        shapefiles = []
        
        for shp_file in shp_files:
            # Handle nested directories
            base_name = os.path.splitext(shp_file)[0]
            shapefiles.append(base_name)
            
        return shapefiles
    
    def _validate_individual_shapefile(self, shapefile_path: str, base_name: str) -> bool:
        """Validate an individual shapefile and track results."""
        shapefile_valid = True
        
        self.validation_details.append(f"\n--- Validating: {base_name} ---")
        
        # Check required files
        if not self._check_required_files(shapefile_path, base_name):
            shapefile_valid = False
        
        # Only proceed with further checks if basic files are present
        if shapefile_valid:
            # Check coordinate system
            if not self._check_coordinate_system(shapefile_path):
                shapefile_valid = False
            
            # Check geometry types
            if not self._check_geometry_types(shapefile_path):
                shapefile_valid = False
            
            # Check coordinate format
            if not self._check_coordinate_format(shapefile_path):
                shapefile_valid = False
        
        return shapefile_valid
    
    def _check_required_files(self, shapefile_path: str, base_name: str) -> bool:
        """Check if all required files are present."""
        base_path = os.path.splitext(shapefile_path)[0]
        missing_files = []
        
        for ext in self.REQUIRED_EXTENSIONS:
            file_path = base_path + ext
            if not os.path.exists(file_path):
                missing_files.append(ext)
        
        if missing_files:
            self.errors.append(f"{base_name}: Missing required files: {', '.join(missing_files)}")
            return False
        
        self.validation_details.append("✓ All required files present (.shp, .shx, .dbf, .prj)")
        return True
    
    def _check_coordinate_system(self, shapefile_path: str) -> bool:
        """Check if coordinate system is WGS84/EPSG:4326."""
        datasource = None
        try:
            driver = ogr.GetDriverByName("ESRI Shapefile")
            datasource = driver.Open(shapefile_path, 0)
            
            if datasource is None:
                self.errors.append(f"Cannot open shapefile: {shapefile_path}")
                return False
            
            layer = datasource.GetLayer()
            spatial_ref = layer.GetSpatialRef()
            
            if spatial_ref is None:
                self.errors.append("No spatial reference system found")
                return False
            
            # Check if it's WGS84
            authority_code = spatial_ref.GetAuthorityCode(None)
            if authority_code == str(self.WGS84_EPSG):
                self.validation_details.append(f"✓ Coordinate system is WGS84 (EPSG:{self.WGS84_EPSG})")
                return True
            
            # Try to identify the CRS
            crs_name = spatial_ref.GetAttrValue("GEOGCS") or "Unknown"
            
            self.errors.append(f"Coordinate system is not WGS84. Found: {crs_name} (EPSG:{authority_code})")
            return False
            
        except Exception as e:
            self.errors.append(f"Error checking coordinate system: {str(e)}")
            return False
        finally:
            if datasource is not None:
                datasource = None
    
    def _check_geometry_types(self, shapefile_path: str) -> bool:
        """Check for 3D (Z) or measured (M) geometry types."""
        datasource = None
        try:
            driver = ogr.GetDriverByName("ESRI Shapefile")
            datasource = driver.Open(shapefile_path, 0)
            
            if datasource is None:
                return False
            
            layer = datasource.GetLayer()
            
            # Check geometry type
            geom_type = layer.GetGeomType()
            geom_name = ogr.GeometryTypeToName(geom_type)
            
            # Check for 3D or measured geometries
            has_z = ogr.GT_HasZ(geom_type)
            has_m = ogr.GT_HasM(geom_type)
            
            if has_z:
                self.errors.append(f"3D geometry (Z values) detected: {geom_name}")
                return False
            
            if has_m:
                self.errors.append(f"Measured geometry (M values) detected: {geom_name}")
                return False
            
            self.validation_details.append(f"✓ Geometry type is valid: {geom_name}")
            return True
            
        except Exception as e:
            self.errors.append(f"Error checking geometry types: {str(e)}")
            return False
        finally:
            if datasource is not None:
                datasource = None
    
    def _check_coordinate_format(self, shapefile_path: str) -> bool:
        """Check if coordinates are in decimal degrees format."""
        datasource = None
        try:
            driver = ogr.GetDriverByName("ESRI Shapefile")
            datasource = driver.Open(shapefile_path, 0)
            
            if datasource is None:
                return False
            
            layer = datasource.GetLayer()
            
            # Get extent to check coordinate ranges
            extent = layer.GetExtent()
            min_x, max_x, min_y, max_y = extent
            
            # Check if coordinates are in reasonable decimal degree ranges
            # Longitude: -180 to 180, Latitude: -90 to 90
            if not (-180 <= min_x <= 180 and -180 <= max_x <= 180):
                self.errors.append(f"Longitude values outside valid range: {min_x:.6f} to {max_x:.6f}")
                return False
            
            if not (-90 <= min_y <= 90 and -90 <= max_y <= 90):
                self.errors.append(f"Latitude values outside valid range: {min_y:.6f} to {max_y:.6f}")
                return False
            
            self.validation_details.append(f"✓ Coordinates are in decimal degrees (Extent: {min_x:.6f}, {min_y:.6f}, {max_x:.6f}, {max_y:.6f})")
            return True
            
        except Exception as e:
            self.errors.append(f"Error checking coordinate format: {str(e)}")
            return False
        finally:
            if datasource is not None:
                datasource = None
    
    def get_validation_report(self) -> str:
        """Generate a comprehensive validation report."""
        report = []
        
        # Add validation details (step-by-step results)
        if self.validation_details:
            report.extend(self.validation_details)
            report.append("")
        
        # Add errors if any
        if self.errors:
            report.append("ERRORS:")
            for error in self.errors:
                report.append(f"  ❌ {error}")
            report.append("")
        
        # Add warnings if any
        if self.warnings:
            report.append("WARNINGS:")  
            for warning in self.warnings:
                report.append(f"  ⚠️  {warning}")
            report.append("")
        
        # Add validation summary (but not final pass/fail status)
        if not self.errors and not self.warnings:
            report.append("All validation checks completed successfully.")
        elif self.errors:
            error_count = len(self.errors)
            warning_count = len(self.warnings)
            if warning_count > 0:
                report.append(f"Validation completed with {error_count} error(s) and {warning_count} warning(s).")
            else:
                report.append(f"Validation completed with {error_count} error(s).")
        elif self.warnings:
            warning_count = len(self.warnings)
            report.append(f"Validation completed with {warning_count} warning(s) but no errors.")
        
        return "\n".join(report)

def main():
    parser = argparse.ArgumentParser(description="Validate shapefiles in ZIP archives")
    parser.add_argument("input", help="Path to ZIP file or directory containing ZIP files")
    parser.add_argument("--batch", action="store_true", help="Process all ZIP files in directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    validator = ShapefileValidator()
    
    if args.batch:
        # Process all ZIP files in directory
        if not os.path.isdir(args.input):
            print(f"ERROR: {args.input} is not a directory")
            sys.exit(1)
        
        zip_files = list(Path(args.input).glob("*.zip"))
        if not zip_files:
            print(f"No ZIP files found in {args.input}")
            sys.exit(1)
        
        print(f"Found {len(zip_files)} ZIP files to validate")
        
        all_valid = True
        for zip_file in zip_files:
            print(f"\n{'='*50}")
            print(f"Processing: {zip_file.name}")
            print(f"{'='*50}")
            
            is_valid, shapefiles = validator.validate_zip_archive(str(zip_file))
            
            if not is_valid:
                all_valid = False
            
            if args.verbose or not is_valid:
                print(validator.get_validation_report())
        
        print(f"\n{'='*50}")
        print("BATCH SUMMARY")
        print(f"{'='*50}")
        if all_valid:
            print("✅ All ZIP files passed validation")
        else:
            print("❌ Some ZIP files failed validation")
        
    else:
        # Process single ZIP file
        if not os.path.exists(args.input):
            print(f"ERROR: File not found: {args.input}")
            sys.exit(1)
        
        print(f"Validating: {args.input}")
        print("="*50)
        
        is_valid, shapefiles = validator.validate_zip_archive(args.input)
        
        if shapefiles:
            print(f"\nFound {len(shapefiles)} shapefile(s):")
            for shp in shapefiles:
                print(f"  - {shp}")
        
        print("\n" + validator.get_validation_report())
        
        if is_valid:
            print(f"\n✅ Validation PASSED for {args.input}")
            sys.exit(0)
        else:
            print(f"\n❌ Validation FAILED for {args.input}")
            sys.exit(1)

if __name__ == "__main__":
    main()