/*
 * FTP Response Capture — postResponseMap hook for FTP Import steps
 *
 * Solves the response_size_exceeded problem by:
 *   1. Keeping responseMapping empty (bypasses 5MB size check)
 *   2. Inspecting FTP response in postResponseMap (runs after size check)
 *   3. Stripping bulk input data (inventory rows no longer needed post-upload)
 *   4. Returning minimal record with only FTP status summary fields
 *
 * Attached to: Bass Pro flow PP[0] (620d41200e97bd3b3b5c94f6)
 */
function captureFtpUploadResult(options) {
  var data = options.data || options.postResponseMapData || [];
  var respData = options.responseData || [];
  var result = [];

  for (var i = 0; i < data.length; i++) {
    var original = data[i];
    var newRec = {};

    // STRIP: Do NOT copy inventory rows from original record.
    // PP[1] only needs FTP status fields — all other Import 2 fields are hardcoded.

    // Capture FTP upload result
    var ftpStatus = 'success';
    var ftpErrorCount = 0;
    var ftpErrorDetail = '';

    if (respData[i] && !respData[i].ignored) {
      var resp = respData[i];
      var body = resp.data || resp.body || resp._json || resp;
      var statusCode = resp.statusCode || (body && body.statusCode) || 0;

      newRec.ftpStatusCode = statusCode;

      // Check for errors in response
      var errors = (body && body.errors) || [];
      if (typeof errors === 'object' && errors.length !== undefined) {
        ftpErrorCount = errors.length;
      }

      if (statusCode >= 400 || ftpErrorCount > 0) {
        ftpStatus = 'error';
        // Capture truncated error detail for EDI history description
        if (ftpErrorCount > 0) {
          ftpErrorDetail = JSON.stringify(errors).substring(0, 500);
        } else if (body && body.message) {
          ftpErrorDetail = String(body.message).substring(0, 500);
        } else {
          ftpErrorDetail = 'HTTP ' + statusCode;
        }
      }
    }

    newRec.ftpStatus = ftpStatus;
    newRec.ftpErrorCount = ftpErrorCount;
    newRec.ftpErrorDetail = ftpErrorDetail;

    // DEBUG: capture raw responseData shape (remove after first successful run)
    try {
      if (respData[i]) {
        newRec._ftpRespDebug = JSON.stringify(respData[i]).substring(0, 500);
      }
    } catch (e) { newRec._ftpRespDebug = 'serialize error: ' + e.message; }

    // Preserve wrapper format
    if (original && typeof original === 'object' && original.data !== undefined) {
      result.push({ data: newRec });
    } else {
      result.push(newRec);
    }
  }

  return result;
}
