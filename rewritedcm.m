function rewritedcm(expfolder,niifile,savedirprefix)
% REWRITEDCM - input expfolder to read dicoms from, nifit data to rewrite
%              saves new dicoms in subdirctory (YYYYMMDD_mlBrainStrip_) of given nifti
%              with series number +200
% TODO: params for outputdir, DCM pattern, +protocolnumber
%

% * reconstructed images are LPI
% * dicoms are RAI
% * nfiles (dcm) can be either sagital or axial
%     - highres: collected sagital (x)
%     - med res: (5min acq) collected axial (z)
%
   addpath('/opt/ni_tools/NlfTI/')
   addpath('/opt/ni_tools/NIfTI/')
   
% rewritedcm('/Volumes/Disk_C/Temp/20170929Luna/DICOM/MP2RAGE_SCOUT/','/Users/lncd/Desktop/slice_warps/david_20170929/anatAndSlice.nii.gz')

    oldpwd=pwd();
    %niidir=cd(cd(fileparts(niifile))); % try to be absolute
    niidir=fileparts(niifile); % relative is not so bad
    savein = [ niidir '/' ];   

    % default save folder prefix to 8 digit date strin + _mlBrainStrip_
    % final directory will also get series description appended
    if nargin ~= 3
       savedirprefix = [datestr(now(),'yyyymmdd_HHMMSS') '_mlBrainStrip_' ];
    end

    cd(expfolder)
    % MP2RGAW 2nd TI image
    optupdown = 1; %1;          % slice order
    maxintensity = 1000;%1000   % ### adjust the value to make 3D rendering better w/o threshold in Siemens 3D    
    bartthreh = 0.5;
    winsize = 3;

    % chen codE:
    %P = [pfolder t1fname]; t1data = load_untouch_nii(P); t1img = double(t1data.img);
    img = load_untouch_nii(niifile);
    Y = double(img.img); % 96 x 118 x 128  % nfiles=96
                         % 184x 210 x 192  % 20180216 1x1x1, nfiles=192
    strfileext = '*.IMA';
    [nfiles,files] = dicom_filelist(strfileext);
    
    uid = dicomuid;
    disp('DICOM conversion - ');
    disp(pwd);
    fprintf('have %d files in %s\n',nfiles,expfolder );
    
    % how were images aquired? how do we put our LPI nifti back to dcm
    firstinfo = dicominfo(files{1});
    acqdir = firstinfo.Private_0051_100e; % 'Tra' vs 'Axl'
    acqmat = [firstinfo.Rows, firstinfo.Columns];
    
    for ll=1:nfiles
        % ;;DICOM read
         
         sliceidx=nfiles-ll +1;
         strfile=files{sliceidx};

         if( mod(sliceidx,10) == 0)
            fprintf('slice %d, %s\n',sliceidx,strfile)
         end

         info = dicominfo(strfile);

         % python
         %   ndataford = numpy.fliplr( numpy.flipud( niidata[(ndcm-1-i),:,:].transpose() ) )
         %data = int16(Y(:,:,ll));
         %data = int16(fliplr(Y(:,:,ll)));
         %data = int16(flipud( fliplr( Y(:,:,ll) ))  ); % -90

         % size(readdicom(strfile)) == 128x118
         % nfiles == 96
         % size(Y) == 96x118x128
         
         % --- med res
         % size(readdicom(strfile)) == 210 x 184
         % nfiles == 196
         % size(Y) == 184 x 210 x 192

         %% LPI -> RAI + file list 
         if strncmp(acqdir,'Tra',3)
             slice=squeeze(Y(:,:,sliceidx)); % 184 x 210
             data = int16(rot90(slice', 2));
         else % axial acq
             slice=squeeze(Y(sliceidx,:,:));
             data = int16(  fliplr( flipud( slice' ))  );
         end
         
         %% modify header
         % data = dicomread(info); % if we were just making a copy
         % ;;SeriesDescription
         SeriesDescription_ = [ savedirprefix info.SeriesDescription]; 
         
         % ;;Series update
         info.SeriesNumber       = info.SeriesNumber + 200;
         info.SeriesDescription  = SeriesDescription_;
         info.SeriesInstanceUID  =  uid;
         
         %% save new dcm (and maybe make a folder)
         % ;;New folder generation
         newfolder = [savein SeriesDescription_];%
         if (ll==1)
             str_command = ['mkdir ' newfolder]; 
             [status,result] = system(str_command); %disp(str_command); 
         end
         % ;;Save
         info.SmallestImagePixelValue = 0;
         info.LargestImagePixelValue = maxintensity;

         %info.WindowCenter = meanval;
         %info.WindowWidth = 4*stdval;
         writeto=[newfolder '/' strfile ];
         %writeto=['/Users/lncd/Desktop/dcmcp/' strfile]
         dicomwrite(data, writeto, info); 

    end
    
    cd(oldpwd)
end

function [n,f] = dicom_filelist(patt)
  f=strsplit(ls(patt));
  keepidx=cellfun(@(x) ~isempty(x), f);
  n=nnz(keepidx);
  f=f(keepidx);
end
