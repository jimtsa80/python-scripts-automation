import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import java.nio.file.attribute.*;
import java.nio.charset.StandardCharsets;

public class ZipSplitter {

    public static void main(String[] args) throws IOException {
        if (args.length < 2) {
            System.out.println("Usage: java ZipSplitter <input_zip> <num_parts>");
            return;
        }

        String inputZip = args[0];
        int numParts = Integer.parseInt(args[1]);

        splitZip(inputZip, numParts);
    }

    private static void splitZip(String inputZip, int numParts) throws IOException {
        String baseName = inputZip.substring(0, inputZip.lastIndexOf('.'));

        try (ZipFile zipFile = new ZipFile(inputZip)) {
            // Create a temporary directory
            Path tempDir = Files.createTempDirectory("zip_splitter");

            // Extract all files into the temporary directory
            System.out.println("Extracting files to temporary directory...");
            Enumeration<? extends ZipEntry> entries = zipFile.entries();
            while (entries.hasMoreElements()) {
                ZipEntry entry = entries.nextElement();
                File entryDestination = new File(tempDir.toFile(), entry.getName());
                entryDestination.getParentFile().mkdirs();
                if (entry.isDirectory()) {
                    entryDestination.mkdirs();
                } else {
                    try (InputStream in = zipFile.getInputStream(entry);
                         OutputStream out = new FileOutputStream(entryDestination)) {
                        byte[] buffer = new byte[1024];
                        int len;
                        while ((len = in.read(buffer)) > 0) {
                            out.write(buffer, 0, len);
                        }
                    }
                }
            }

            // Get a list of all files in the temporary directory and sort them
            System.out.println("Collecting and sorting file paths...");
            List<Path> filePaths = new ArrayList<>();
            Files.walk(tempDir).filter(Files::isRegularFile).forEach(filePaths::add);
            Collections.sort(filePaths);

            // Determine the total size and size of each part
            long totalSize = filePaths.stream().mapToLong(p -> p.toFile().length()).sum();
            long partSize = totalSize / numParts;
            long remainingSize = totalSize % numParts;

            // Adjust part size for distribution
            if (remainingSize > 0) {
                partSize++;
                remainingSize--;
            }

            // Create split ZIP files
            int partNum = 1;
            long currentSize = 0;
            ZipOutputStream currentZip = new ZipOutputStream(new FileOutputStream(String.format("part%d_%s.zip", partNum, baseName)));

            for (Path filePath : filePaths) {
                long fileSize = Files.size(filePath);

                if (currentSize + fileSize > partSize) {
                    currentZip.close();
                    printJpegInfo(String.format("part%d_%s.zip", partNum, baseName));
                    partNum++;
                    if (partNum > numParts) {
                        break;
                    }
                    if (remainingSize > 0) {
                        partSize--;
                        remainingSize--;
                    }
                    currentSize = 0;
                    currentZip = new ZipOutputStream(new FileOutputStream(String.format("part%d_%s.zip", partNum, baseName)));
                }

                try (InputStream in = Files.newInputStream(filePath)) {
                    currentZip.putNextEntry(new ZipEntry(tempDir.relativize(filePath).toString()));
                    byte[] buffer = new byte[1024];
                    int len;
                    while ((len = in.read(buffer)) > 0) {
                        currentZip.write(buffer, 0, len);
                    }
                    currentZip.closeEntry();
                }

                currentSize += fileSize;
            }

            if (partNum <= numParts) {
                currentZip.close();
                printJpegInfo(String.format("part%d_%s.zip", partNum, baseName));
            }

            // Clean up the temporary directory
            Files.walkFileTree(tempDir, new SimpleFileVisitor<Path>() {
                @Override
                public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) throws IOException {
                    Files.delete(file);
                    return FileVisitResult.CONTINUE;
                }

                @Override
                public FileVisitResult postVisitDirectory(Path dir, IOException exc) throws IOException {
                    Files.delete(dir);
                    return FileVisitResult.CONTINUE;
                }
            });
        }
    }

    private static void printJpegInfo(String zipPath) throws IOException {
        int numImages = 0;
        String firstJpeg = null;
        String lastJpeg = null;

        try (ZipFile zipFile = new ZipFile(zipPath)) {
            Enumeration<? extends ZipEntry> entries = zipFile.entries();

            while (entries.hasMoreElements()) {
                ZipEntry entry = entries.nextElement();
                String filename = entry.getName().toLowerCase();
                if (filename.endsWith(".jpg") || filename.endsWith(".jpeg")) {
                    numImages++;
                    if (firstJpeg == null) {
                        firstJpeg = entry.getName();
                    }
                    lastJpeg = entry.getName();
                }
            }
        }

        if (numImages > 0) {
            System.out.printf("Total JPEGs in %s: %d%n", zipPath, numImages);
            System.out.printf("First JPEG: %s%n", firstJpeg);
            System.out.printf("Last JPEG: %s%n", lastJpeg);
        } else {
            System.out.printf("No JPEGs found in %s%n", zipPath);
        }
    }
}
